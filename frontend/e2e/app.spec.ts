import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.getByLabel("Username").fill("owner");
  await page.getByLabel("Password").fill("change-this-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/dashboard/);
});

test("shows dashboard KPIs and P&L", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Monthly P&L")).toBeVisible();
  await expect(page.getByText("Sales revenue")).toBeVisible();
});

test("navigates between primary pages", async ({ page }) => {
  await page.getByRole("link", { name: "Entries" }).click();
  await expect(page.getByRole("heading", { name: "Entries" })).toBeVisible();
  await page.getByRole("button", { name: "Recurring expenses" }).click();
  await expect(page.getByRole("heading", { name: "Add recurring expense" })).toBeVisible();
  await page.getByRole("link", { name: "Inventory" }).click();
  await expect(page.getByRole("heading", { name: "Inventory", exact: true })).toBeVisible();
});

test("validates the inventory entry flow", async ({ page }) => {
  await page.getByRole("link", { name: "Inventory" }).click();
  const itemCode = `PW-${Date.now()}`;
  await page.getByRole("textbox", { name: "Item code" }).fill(itemCode);
  await page.getByRole("textbox", { name: "Purchase price" }).fill("500");
  await page.getByRole("button", { name: "Add item" }).click();
  await expect(page.getByText(itemCode, { exact: true })).toBeVisible();
});

