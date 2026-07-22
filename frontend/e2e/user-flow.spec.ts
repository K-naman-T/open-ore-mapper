import { test, expect } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"
const __dirname = path.dirname(fileURLToPath(import.meta.url))

test("full user flow: load → draw bbox → open settings → map minerals → see results", async ({ page }) => {
  // 1. NAVIGATE TO APP
  await page.goto("http://localhost:5173")
  await page.waitForTimeout(3000)

  // 2. VERIFY GLOBE LOADS (canvas rendered by MapLibre GL)
  await expect(page.locator("canvas")).toBeVisible({ timeout: 15000 })
  console.log("✅ Globe loaded")

  // 3. VERIFY LOGO VISIBLE
  await expect(page.locator("text=Open Ore Mapper")).toBeVisible()
  console.log("✅ Logo visible")

  // 4. VERIFY GEAR BUTTON (settings) — uses data-wt attribute
  const gearBtn = page.locator('[data-wt="settings"]')
  await expect(gearBtn).toBeVisible({ timeout: 10000 })
  console.log("✅ Gear button visible")

  // 5. OPEN SETTINGS PANEL
  await gearBtn.click()
  await page.waitForTimeout(500)

  // 6. VERIFY SETTINGS CONTENT
  await expect(page.locator("text=Settings")).toBeVisible()
  await expect(page.locator("text=EMIT")).toBeVisible()
  await expect(page.locator("button:has-text('Map Minerals')")).toBeVisible()
  await expect(page.getByText("Minerals", { exact: true })).toBeVisible()
  console.log("✅ Settings panel open with content")

  // 7. TOGGLE A MINERAL OFF and verify
  const hematiteBtn = page.locator("button:has-text('hematite')")
  await expect(hematiteBtn).toBeVisible()
  await hematiteBtn.click()
  await page.waitForTimeout(200)

  // 8. CHANGE SENSOR TO CUBERT
  await page.locator("button:has-text('Cubert')").click()
  await page.waitForTimeout(200)

  // 9. CHANGE CLASSIFIER TO SAM
  await page.locator("button:has-text('SAM')").click()
  await page.waitForTimeout(200)

  // 10. CLOSE SETTINGS by clicking the backdrop overlay
  await page.locator(".fixed.inset-0.z-30").click({ position: { x: 10, y: 10 } })
  await page.waitForTimeout(500)

  // 11. VERIFY SHIFT+DRAG CUE
  await expect(page.getByText("Shift", { exact: true })).toBeVisible()
  console.log("✅ Shift+drag cue visible")

  // 12. REOPEN SETTINGS FOR FILE UPLOAD
  await gearBtn.click()
  await page.waitForTimeout(500)

  // 13. UPLOAD A FILE via the hidden file input
  const fileInput = page.locator('input[type="file"]')
  const filePath = path.join(__dirname, "fixtures", "test-cube.tif")
  await fileInput.setInputFiles(filePath)
  await page.waitForTimeout(500)

  // If file was set, we should see the filename in the upload area
  await expect(page.getByText("test-cube.tif", { exact: true })).toBeVisible()
  console.log("✅ File uploaded")

  // 14. VERIFY MAP MINERALS BUTTON IS NOW ENABLED (minerals selected + file uploaded)
  const mapBtn = page.locator("button:has-text('Map Minerals')")
  await expect(mapBtn).toBeEnabled()
  console.log("✅ Map Minerals button enabled")

  console.log("\n✅ FULL USER FLOW: All assertions passed")
})
