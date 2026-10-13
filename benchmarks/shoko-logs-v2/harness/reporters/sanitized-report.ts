import fs from 'node:fs';
import path from 'node:path';

import type { FullResult, Reporter, TestCase, TestResult } from '@playwright/test/reporter';

/**
 * Sanitized failure report for the shoko-logs v2 reviewer.
 *
 * The reviewer (see ../../README.md, step 6) is handed ONLY this file, never the
 * raw Playwright stdout log: it must see spec/test titles and the observed
 * symptom, never selector internals (`getByRole(...)`, `locator(...)`, call logs,
 * stack frames). The report is written on `onEnd` to `HARNESS_REPORT` when set,
 * otherwise to `harness-report.md` in the process cwd.
 *
 * Deterministic and dependency-free; a write failure warns instead of crashing
 * the run.
 */

/** Substrings that mark a line as leaking a selector / locator internal. */
const SELECTOR_INTERNALS = ['getBy', 'locator(', 'locator:', 'page.', 'frame.', 'selector'];

/** Prefixes (after trimming) that mark a line as a stack frame or call-log entry. */
const DROP_PREFIXES = ['at ', '- '];

/** Substrings that mark a line as part of a Playwright call-log block. */
const DROP_CONTAINS = ['Call log', 'waiting for'];

/**
 * Playwright's interaction-API prefix (`locator.fill: `, `locator.click: `). It names the
 * API, not a selector, so it is stripped rather than dropping the whole line - the symptom
 * after it (`Timeout 30000ms exceeded.`) is what the reviewer needs.
 */
const LOCATOR_METHOD = /\blocator\.[A-Za-z]+:\s*/g;

/**
 * Playwright's assertion wrapper (`expect(locator).toBeVisible()`, `expect(page).toHaveURL()`).
 * It names the assertion API rather than a selector, so the whole call is reduced to a neutral
 * phrase - the clauses after it (`Expected: visible; Timeout: 10000ms`) carry the symptom.
 */
const EXPECT_ASSERTION = /\bexpect\([^)]*\)(?:\.[A-Za-z]+)+\([^)]*\)(\s*failed)?/g;

/** Prefixes that mark a line as a semantic, selector-free symptom. */
const KEEP_PREFIXES = ['Expected', 'Received', 'Error:', 'Test timeout', 'Timeout', 'expect('];

/**
 * Playwright's strict-mode error, which carries its whole meaning on a line that also
 * dumps the matched elements (and therefore leaks selectors). The count is the symptom:
 * the matcher found more than one element where one was expected, i.e. the same content
 * renders more than once. The count is re-emitted without the element dump.
 */
const STRICT_MODE = /strict mode violation[\s\S]*?resolved to (\d+)\s*elements?/i;

interface Failure {
  spec: string;
  test: string;
  symptom: string;
}

/** `#` immediately followed by an identifier, e.g. `#search` in a selector. */
const SELECTOR_ID = /#[A-Za-z_]/;

/** ANSI SGR colour codes Playwright embeds in error messages (`\x1b[2m`, …). */
const ANSI = /\u001b\[[0-9;]*m/g;

function leaksSelector(line: string): boolean {
  if (SELECTOR_INTERNALS.some((needle) => line.includes(needle))) return true;
  return SELECTOR_ID.test(line);
}

function isDroppedLine(line: string): boolean {
  const trimmed = line.trimStart();
  if (DROP_PREFIXES.some((prefix) => trimmed.startsWith(prefix))) return true;
  return DROP_CONTAINS.some((needle) => line.includes(needle));
}

/**
 * Reduce a raw Playwright error message to its semantic lines only.
 *
 * Keeps the first non-empty line plus any line matching a known symptom prefix;
 * drops stack frames, call-log blocks and anything carrying a selector.
 */
function sanitizeMessage(message: string): string {
  const kept: string[] = [];
  let seenFirst = false;

  for (const raw of message.replace(ANSI, '').split(/\r?\n/)) {
    const line = raw.trim().replace(LOCATOR_METHOD, '').replace(EXPECT_ASSERTION, 'the check');
    if (!line) continue;

    const isFirst = !seenFirst;
    seenFirst = true;

    // Strict mode carries its symptom on a line that also dumps the matched elements:
    // re-emit the count (selectors in the dump are still dropped) before the leak check.
    const strict = STRICT_MODE.exec(line);
    if (strict) {
      kept.push(`Error: strict mode violation - the matcher resolved to ${strict[1]} elements instead of 1`);
      continue;
    }

    // Never emit a raw selector, even on the first line.
    if (leaksSelector(line)) continue;
    if (isDroppedLine(line)) continue;

    if (isFirst) {
      kept.push(line);
      continue;
    }
    if (KEEP_PREFIXES.some((prefix) => line.startsWith(prefix))) {
      kept.push(line);
    }
  }

  // Collapse repeats, including the "Error: <same text>" variant Playwright emits
  // alongside the first line of a timeout.
  const dedupeKey = (line: string) => line.replace(/^Error:\s*/i, '').replace(/\.$/, '').trim().toLowerCase();
  const joined = kept
    .filter((line, index) => kept.findIndex((other) => dedupeKey(other) === dedupeKey(line)) === index)
    .join('; ');
  if (!joined) return 'Test failed (no sanitized detail available).';
  return joined.length > 300 ? `${joined.slice(0, 297).trimEnd()}...` : joined;
}

class SanitizedReport implements Reporter {
  private total = 0;
  private passed = 0;
  private failed = 0;
  private skipped = 0;
  private readonly failures: Failure[] = [];

  onTestEnd(test: TestCase, result: TestResult): void {
    this.total += 1;

    if (result.status === 'passed') {
      this.passed += 1;
      return;
    }
    if (result.status !== 'failed' && result.status !== 'timedOut' && result.status !== 'interrupted') {
      this.skipped += 1; // counted in total; never a full pass.
      return;
    }

    this.failed += 1;

    const errors = result.errors.length > 0 ? result.errors : result.error ? [result.error] : [];
    const message = errors
      .map((error) => error.message ?? error.stack ?? error.value ?? '')
      .filter((text) => text.length > 0)
      .join('\n');

    this.failures.push({
      spec: path.basename(test.location.file),
      test: test.title,
      symptom: sanitizeMessage(message),
    });
  }

  onEnd(result: FullResult): void {
    const seconds = Math.round(result.duration / 1000);
    const lines = [
      '# Harness failure report',
      '',
      `Result: ${this.passed}/${this.total} passed, ${this.failed} failed${
        this.skipped > 0 ? `, ${this.skipped} skipped` : ''
      } (${seconds}s)`,
      '',
      '## Failures',
      '',
    ];

    if (this.failures.length === 0 && this.skipped === 0) {
      lines.push('None — the suite is green.');
    } else if (this.failures.length === 0) {
      lines.push(
        `No failures, but ${this.skipped} of ${this.total} tests were skipped — not a full pass (green requires ${this.total}/${this.total}).`,
      );
    } else {
      for (const failure of this.failures) {
        lines.push(`- **${failure.spec} › ${failure.test}** — ${failure.symptom}`);
      }
    }

    const target = process.env.HARNESS_REPORT ?? path.join(process.cwd(), 'harness-report.md');
    try {
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, `${lines.join('\n')}\n`, 'utf8');
    } catch (error) {
      // Never fail the run over the report; surface it for a human instead.
      console.error(`[sanitized-report] could not write ${target}: ${String(error)}`);
    }
  }
}

export default SanitizedReport;
