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

public class BrowseTest {
    static By BROWSE_PAGE_FORM_TITLE = By.xpath(".//*[@id='content']/div/h1");
    static By BROWSE_PAGE_SUB_TITLE = By.xpath
            (".//*[@id='content']/div/section/div[2]/h3");
    static By BROWSE_PAGE_SECTION_TITLE = By.xpath
            (".//*[@id='instance-list']/div/h3");
    static By BROWSE_PAGE_HELP_TEXT_1 = By.xpath
            (".//*[@id='content']/div/ul/li[1]");
    static By BROWSE_PAGE_HELP_TEXT_2 = By.xpath
            (".//*[@id='content']/div/ul/li[2]");
    static By OPEN_MANAGE_DROPDOWN = By.xpath
            ("//li[@class='setup dropdown']/a/span[2]");
    static By NAVIGATE_TO_NOTIFICATION_PAGE = By.xpath
            ("//a[@href='/YOMP/notify']");
    static By BROWSE_PAGE_INSTANCE_LIST_HEADING = By.xpath
            (".//*[@id='content']/div/section/div[2]/p");
    static By BROWSE_US_WEST_2 = By.xpath
            (".//*[@id='network-tree']/ul/li[8]/div/span");
    static By BROWSE_REGION = By.xpath
            (".//*[@id='network-tree']/ul/li[8]/ul/li[4]/div/span");
    static By BROWSE_INSTANCE = By.xpath
            (".//*[@id='network-tree']/ul/li[8]/ul/li[4]/ul/li[1]/div/span");
    static By BROWSE_SELECT_INSTANCE = By.xpath
            (".//*[@id='instance-list']/div/form/table/tbody/tr[1]/td[1]/a");
    static By BROWSE_DONE_BUTTON = By.xpath
            ("//button[@data-bb-handler='done']");
    static By BROWSE_METRIC = By.xpath
            ("html/body/div[3]/div/div/div[2]/div/div/ol/li[1]/div/div/div/span[1]");
    static By BROWSE_SELECT_METRIC = By.xpath
            ("html/body/div[3]/div/div/div[1]/h4");
    static int WAIT_TIME = 10;

    public static void browsePageTitleVerification(WebDriver driver) {
        String browsePageTitle = driver.findElement(BROWSE_PAGE_FORM_TITLE)
                .getText();
        String browseSubTitle = driver.findElement(BROWSE_PAGE_SUB_TITLE)
                .getText();
        String browseSectionTitle = driver.findElement(BROWSE_PAGE_SECTION_TITLE)
                .getText();
        Assert.assertEquals(browsePageTitle, "Browse Instances");
        Assert.assertEquals(browseSubTitle, "Explore and Choose Instances");
        Assert.assertEquals(browseSectionTitle,
                "Instances Currently Monitored by YOMP");
    }

    public static void browsePageHelpTextVerification(WebDriver driver) {
        String browsePageHelpText1 = driver.findElement
                (BROWSE_PAGE_HELP_TEXT_1).getText();
        String browsePageHelpText2 = driver.findElement
                (BROWSE_PAGE_HELP_TEXT_2).getText();
        Assert.assertEquals(browsePageHelpText1, "On the left, expand regions "
                + "and services and click on an instance name to select.");
        Assert.assertEquals(browsePageHelpText2, "Instances that have been "
                + "selected for monitoring will be listed on the right, where"
                + " they can be edited or removed.");
    }

    public static void browsePageSelectInstance(WebDriver driver) {
        TestUtilities.waitClick(BROWSE_US_WEST_2, driver, WAIT_TIME);
        TestUtilities.waitClick(BROWSE_REGION, driver, WAIT_TIME);
        TestUtilities.waitClick(BROWSE_INSTANCE, driver, WAIT_TIME);
    }

    public static void browseClickOnInstance(WebDriver driver) {
        TestUtilities.waitClick(BROWSE_SELECT_INSTANCE, driver, WAIT_TIME);
        String browseSelectMetric = TestUtilities.waitGetText
                (BROWSE_SELECT_METRIC, driver, WAIT_TIME);
        Assert.assertEquals(browseSelectMetric, "Select Metrics to Monitor");
        TestUtilities.waitClick(BROWSE_METRIC, driver, WAIT_TIME);
        TestUtilities.waitClick(BROWSE_DONE_BUTTON, driver, WAIT_TIME);
    }

    public static void browsePageSectionTitleVerification(WebDriver driver) {
        ReusableTests
        .testInstancesCurrentlyMonitoredByYOMPTitleVerification(driver);
    }

    public static void browseColumnVerification(WebDriver driver) {
        ReusableTests
        .testInstancesCurrentlyMonitoredByYOMPColumnNamesVerification(driver);
    }

    public static void browseHeader(WebDriver driver)
      throws InterruptedException {
        ReusableTests.testHeaderAfterSetup(driver);
    }

    public static void browseFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void browseExportAndRemoveButtonsVerification(WebDriver driver) {
        ReusableTests.testRemoveButtonVerfication(driver);
        ReusableTests.testExportButtonVerfication(driver);
    }

    public static void navigateNotificationPage(WebDriver driver)
      throws InterruptedException {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        TestUtilities.waitClick(NAVIGATE_TO_NOTIFICATION_PAGE, driver,
                WAIT_TIME);
    }
}
