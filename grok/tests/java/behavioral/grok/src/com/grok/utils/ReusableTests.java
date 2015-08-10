/*
 * Numenta Platform for Intelligent Computing (NuPIC)
 * Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
 * Numenta, Inc. a separate commercial license for this software code, the
 * following terms and conditions apply:
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 3 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses.
 *
 * http://numenta.org/licenses/
 *
 */

package com.YOMP.utils;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import org.testng.Assert;

public class ReusableTests {
    static By SETUP_PROGRESS_TEXT = By
            .xpath("html/body/div[1]/section/div/div/section/div/div/div[1]");
    static By INSTANCE_COLUMN = By.xpath("//tr/th[1]");
    static By SERVICE_COLUMN = By.xpath("//tr/th[2]");
    static By REGION_COLUMN = By.xpath("//tr/th[3]");
    static By STATUS_COLUMN = By.xpath("//tr/th[4]");
    static By REMOVE_COLUMN = By.xpath("//tr/th[5]");
    static By LOGIN_BUTTON_LOCATOR = By.id("next");
    static By EXPORT_BUTTON = By
            .xpath("//button[@class='export btn btn-default']");
    static By REMOVE_BUTTON = By
            .xpath("//button[@class='delete btn btn-default']");
    static By INSTANCES_CURRENTLY_MONITORED_BY_YOMP_TITLE = By
            .xpath("//div[@id='instance-list']/div/h3");
    static By DONE_BUTTON = By.xpath("//button[@id='done']");
    static int WAIT_TIME = 10;

    public static void testFooter(WebDriver driver) throws Exception {
        FooterPageObject footer = new FooterPageObject(driver);
        String YOMP_footer_about = footer.aboutLink();
        String YOMP_footer_help = footer.helpLink();
        String YOMP_footer_numenta = footer.numentaLink();
        Assert.assertEquals(YOMP_footer_about, "About");
        Assert.assertEquals(YOMP_footer_help, "Help");
        Assert.assertEquals(YOMP_footer_numenta, "Numenta");
    }

    public static void testHeaderDuringSetup(WebDriver driver)
            throws InterruptedException {
        HeaderPageObject header = new HeaderPageObject(driver);
        String YOMP_logo = header.YOMPLogo();
        String YOMP_help = header.helpLogo();
        Assert.assertEquals(YOMP_logo, "YOMP");
        Assert.assertEquals(YOMP_help, "Help");
    }

    public static void testHeaderAfterSetup(WebDriver driver)
            throws InterruptedException {
        HeaderPageObject header = new HeaderPageObject(driver);
        testHeaderDuringSetup(driver);
        boolean YOMPSetup = header.setupDropDown();
        boolean YOMPCharts = header.chartsTab();
        boolean YOMPManage = header.manageTab();
        Assert.assertEquals(YOMPCharts, true);
        Assert.assertEquals(YOMPManage, true);
        Assert.assertEquals(YOMPSetup, true);
    }

    public static void testSetUpProgressText(WebDriver driver)
            throws InterruptedException {
        WebDriverWait wait = new WebDriverWait(driver, WAIT_TIME);
        String str = wait.until(
                ExpectedConditions
                        .presenceOfElementLocated(SETUP_PROGRESS_TEXT))
                .getText();
        Assert.assertEquals(str, "Setup Progress:");
    }

    public static void testInstancesCurrentlyMonitoredByYOMPColumnNamesVerification(
            WebDriver driver) {
        String instanceColumn1 = TestUtilities.waitGetText(INSTANCE_COLUMN,
                driver, WAIT_TIME);
        String serviceColumn2 = TestUtilities.waitGetText(SERVICE_COLUMN,
                driver, WAIT_TIME);
        String regionColumn3 = TestUtilities.waitGetText(REGION_COLUMN, driver,
                WAIT_TIME);
        String statusColumn4 = TestUtilities.waitGetText(STATUS_COLUMN, driver,
                WAIT_TIME);
        String removeColumn5 = TestUtilities.waitGetText(REMOVE_COLUMN, driver,
                WAIT_TIME);
        Assert.assertEquals(instanceColumn1, "Instance");
        Assert.assertEquals(serviceColumn2, "Service");
        Assert.assertEquals(regionColumn3, "Region");
        Assert.assertEquals(statusColumn4, "Status");
        Assert.assertEquals(removeColumn5, "Remove");
    }

    public static void testSubmitLogin(WebDriver driver) {
        driver.findElement(LOGIN_BUTTON_LOCATOR).click();
    }

    public static void testExportButtonVerfication(WebDriver driver) {
        String ExportAllButtonVerfication = TestUtilities.waitGetText(
                EXPORT_BUTTON, driver, WAIT_TIME);
        Assert.assertEquals(ExportAllButtonVerfication, "Export All");
    }

    public static void testRemoveButtonVerfication(WebDriver driver) {
        String RemoveAllButtonVerfication = TestUtilities.waitGetText(
                REMOVE_BUTTON, driver, WAIT_TIME);
        Assert.assertEquals(RemoveAllButtonVerfication, "Remove All");
    }

    public static void testInstancesCurrentlyMonitoredByYOMPTitleVerification(
            WebDriver driver) {
        String instancesCurrentlyMonitoredByYOMPSectionTitle = TestUtilities
                .waitGetText(INSTANCES_CURRENTLY_MONITORED_BY_YOMP_TITLE,
                        driver, WAIT_TIME);
        Assert.assertEquals(instancesCurrentlyMonitoredByYOMPSectionTitle,
                "Instances Currently Monitored by YOMP");
    }

    public static void testDoneButtonVerification(WebDriver driver) {
        String doneButtonVerification = TestUtilities.waitGetText(DONE_BUTTON,
                driver, WAIT_TIME);
        Assert.assertEquals(doneButtonVerification, "Done");
    }
}
