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

package com.YOMP.tests;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.testng.Assert;

import com.YOMP.utils.ReusableTests;
import com.YOMP.utils.TestUtilities;

public class ImportTest {
    static By IMPORT_FORM_TITLE = By.xpath("html/body/div[1]/section/div/h1");
    static By IMPORT_SUB_TITLE = By
            .xpath("html/body/div[1]/section/div/section/div[2]/h3");
    static By IMPORT_SECTION_TITLE = By
            .xpath("html/body/div[1]/section/div/section/div[1]/div/div/h3");
    static By IMPORT_HELP_BLOCK2 = By
            .xpath("html/body/div[1]/section/div/ul/li[2]");
    static By IMPORT_HELP_BLOCK3 = By
            .xpath("html/body/div[1]/section/div/ul/li[3]");
    static By IMPORT_LABEL_FILE_TO_IMPORT = By
            .xpath("html/body/div[1]/section/div/section/div[2]/form/div/label");
    static By IMPORT_DONE_BUTTON = By.xpath("//button[@id='done']");
    static By IMPORT_CHOOSE_FILE_BUTTON = By.xpath("//input[@id='file']");
    static By OPEN_MANAGE_DROPDOWN = By
            .xpath("//li[@class='setup dropdown']/a/span[2]");
    static By NAVIGATE_TO_AUTOSTACK_PAGE = By
            .xpath("//li[@class='setup dropdown open']/ul/li[5]");
    static int WAIT_TIME = 10;

    public static void importTitleVerification(WebDriver driver) {
        String importPageTitle = TestUtilities.waitGetText(IMPORT_FORM_TITLE,
                driver, WAIT_TIME);
        String importSubTitle = TestUtilities.waitGetText(IMPORT_SUB_TITLE,
                driver, WAIT_TIME);

        Assert.assertEquals(importPageTitle, "Import Selections");
        Assert.assertEquals(importSubTitle,
                "Upload Previously Saved Configuration File");
    }

    public static void importHelpTextVerification(WebDriver driver) {
        String importHelpText2 = TestUtilities.waitGetText(IMPORT_HELP_BLOCK2,
                driver, WAIT_TIME);
        String importHelpText3 = TestUtilities.waitGetText(IMPORT_HELP_BLOCK3,
                driver, WAIT_TIME);
        Assert.assertEquals(importHelpText2,
                "New instances will be selected for monitoring, duplicates will be ignored.");
        Assert.assertEquals(importHelpText3,
                "This process can take several minutes to complete.");
    }

    public static void importButtonVerification(WebDriver driver) {
        String importChooseFileButton = TestUtilities.waitGetText(
                IMPORT_CHOOSE_FILE_BUTTON, driver, WAIT_TIME);
        Assert.assertEquals(importChooseFileButton, "Choose File");

    }

    public static void importColumnVerification(WebDriver driver) {
        ReusableTests
                .testInstancesCurrentlyMonitoredByYOMPColumnNamesVerification(driver);
    }

    public static void importHeader(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testHeaderAfterSetup(driver);
    }

    public static void importFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void importExportRemoveButtonVerification(WebDriver driver) {
        ReusableTests.testRemoveButtonVerfication(driver);
        ReusableTests.testExportButtonVerfication(driver);
    }

    public static void importSectionTitleVerification(WebDriver driver) {
        ReusableTests
                .testInstancesCurrentlyMonitoredByYOMPTitleVerification(driver);
    }

    public static void importDoneButtonVerification(WebDriver driver) {
        ReusableTests.testDoneButtonVerification(driver);
    }
}