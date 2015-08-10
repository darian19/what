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

public class CustomMetricTest {
    static By CUSTOM_METRIC_FORM_TITLE = By
            .xpath(".//*[@id='content']/div/div/h1");
    static By CUSTOM_METRIC_SUB_TITLE =  By
            .xpath(".//*[@id='content']/div/div/div/h3");
    static By CUSTOM_METRIC_HELP_TEXT = By
            .xpath("html/body/div[1]/section/div/section/div[1]/div/div/h3");
    static By IMPORT_DONE_BUTTON = By.xpath("//button[@id='done']");
    static By OPEN_MANAGE_DROPDOWN = By
            .xpath("//li[@class='setup dropdown']/a/span[2]");
    static By NAVIGATE_TO_IMPORT_PAGE = By
            .xpath("//a[@href='/YOMP/instances/import']");
    static int WAIT_TIME = 10;

    public static void customMetricPageTitleVerification(WebDriver driver) {
        String customMetricPageTitle = TestUtilities.waitGetText
                (CUSTOM_METRIC_FORM_TITLE, driver, WAIT_TIME);
        String customMetricSubTitle = TestUtilities.waitGetText
                (CUSTOM_METRIC_SUB_TITLE, driver, WAIT_TIME);
        Assert.assertEquals(customMetricPageTitle, "Manage Custom Metrics");
        Assert.assertEquals(customMetricSubTitle,
                "Custom Metrics Recorded by YOMP");
    }

    public static void customMetricHelpTextVerification(WebDriver driver) {
        String customMetricHelpText = TestUtilities.waitGetText
                (CUSTOM_METRIC_HELP_TEXT, driver, WAIT_TIME);
        Assert.assertEquals(customMetricHelpText,
                "No custom metrics exist.");
    }

    public static void customMetricHeader(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testHeaderAfterSetup(driver);
    }

    public static void customMetricFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void customMetricDoneButtonVerification(WebDriver driver) {
        ReusableTests.testDoneButtonVerification(driver);
    }

    public static void navigateImport(WebDriver driver) {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        TestUtilities.waitClick(NAVIGATE_TO_IMPORT_PAGE, driver, WAIT_TIME);
    }
}
