import { expect, test } from "@playwright/test";

const e2eUsername = process.env.E2E_USERNAME ?? "hema";
const e2ePassword = process.env.E2E_PASSWORD ?? "hema1234";

async function expectNoHorizontalOverflow(page: import("@playwright/test").Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    )
    .toBe(true);
}

async function expectMobileFormControlsAtLeast16px(page: import("@playwright/test").Page) {
  await expect
    .poll(() =>
      page.locator("input, select, textarea").evaluateAll((controls) =>
        controls.every((control) => getComputedStyle(control).fontSize === "16px"),
      ),
    )
    .toBe(true);
}

async function expectTemporalControlsWebKitSafe(page: import("@playwright/test").Page) {
  await expect
    .poll(() =>
      page.locator('input[type="date"], input[type="month"]').evaluateAll((controls) =>
        controls.every((control) => {
          const style = getComputedStyle(control);
          return style.padding === "0px" && Number.parseFloat(style.minHeight) >= 44;
        }),
      ),
    )
    .toBe(true);
}

test.beforeEach(async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.getByLabel("Username").fill(e2eUsername);
  await page.getByLabel("Password").fill(e2ePassword);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/dashboard/);
});

test("shows dashboard KPIs and P&L", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Sales", { exact: true })).toBeVisible();
  await expect(page.getByText("Operating profit", { exact: true })).toBeVisible();
  await expect(page.getByText("Unsold items", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Needs attention", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Inventory ageing" })).toBeVisible();
  await expect(page.getByText("0–30 days", { exact: true })).toBeVisible();
  await expect(page.getByText("90+ days", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "12-month P&L" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Show detailed reports" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Monthly P&L" })).toHaveCount(0);
});

test("shows the compact 12-month P&L chart in detailed reports", async ({ page }) => {
  await page.getByRole("button", { name: "Show detailed reports" }).click();
  await expect(page.getByRole("heading", { name: "12-month P&L" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Monthly P&L" })).toBeVisible();
  await expect(page.getByText("Sales revenue")).toBeVisible();
  await expect(page.getByRole("img", { name: "12-month net operating profit bar chart" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Inventory ageing" })).toHaveCount(1);
});

test("navigates between primary pages", async ({ page }) => {
  await page.getByRole("link", { name: "Entries" }).click();
  await expect(page.getByRole("heading", { name: "Entries" })).toBeVisible();
  await page.getByRole("tab", { name: "Recurring expenses" }).click();
  await expect(page.getByRole("heading", { name: "Add recurring expense" })).toBeVisible();
  await page.getByRole("link", { name: "Inventory" }).click();
  await expect(page.getByRole("heading", { name: "Inventory", exact: true })).toBeVisible();
});

test("shows authenticated build diagnostics outside primary navigation", async ({ page }) => {
  await page.goto("/diagnostics", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Diagnostics" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Frontend" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "API" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Diagnostics" })).toHaveCount(0);
});

test("keeps date and month fields inside mobile layouts", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto("/dashboard", { waitUntil: "networkidle" });
  await expect(page.locator(".dashboard-month-selector input")).toBeVisible();
  await expectMobileFormControlsAtLeast16px(page);
  await expectTemporalControlsWebKitSafe(page);
  await expectNoHorizontalOverflow(page);

  await page.getByRole("link", { name: "Entries" }).click();
  await expect(page.locator('input[type="date"]')).toBeVisible();
  await expectMobileFormControlsAtLeast16px(page);
  await expectTemporalControlsWebKitSafe(page);
  await expectNoHorizontalOverflow(page);

  await page.getByRole("tab", { name: "Recurring expenses" }).click();
  await expect(page.locator('input[type="month"]')).toBeVisible();
  await expectMobileFormControlsAtLeast16px(page);
  await expectTemporalControlsWebKitSafe(page);
  await expectNoHorizontalOverflow(page);

  await page.getByRole("tab", { name: "Other expenses" }).click();
  await expect(page.locator('input[type="date"]')).toBeVisible();
  await expectMobileFormControlsAtLeast16px(page);
  await expectTemporalControlsWebKitSafe(page);
  await expectNoHorizontalOverflow(page);

  await page.getByRole("link", { name: "Inventory" }).click();
  await expect(page.locator('input[type="date"]')).toBeVisible();
  await expectMobileFormControlsAtLeast16px(page);
  await expectTemporalControlsWebKitSafe(page);
  await expectNoHorizontalOverflow(page);
});

test("keeps login controls at 16px on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto("/", { waitUntil: "networkidle" });
  await expectMobileFormControlsAtLeast16px(page);
  await expect(page.getByLabel("Password")).toHaveCSS("font-size", "16px");
});

test("validates the inventory entry flow", async ({ page }) => {
  await page.getByRole("link", { name: "Inventory" }).click();
  const itemCode = `PW-${Date.now()}`;
  await page.getByRole("textbox", { name: "Item code" }).fill(itemCode);
  await page.getByRole("textbox", { name: "Purchase price" }).fill("500");
  await page.getByRole("button", { name: "Add item" }).click();
  await expect(page.getByText(itemCode, { exact: true })).toBeVisible();
});

