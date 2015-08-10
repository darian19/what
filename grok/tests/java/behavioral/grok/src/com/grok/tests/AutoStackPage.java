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

import com.YOMP.utils.ReusableTests;
import com.YOMP.utils.TestUtilities;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.Select;
import org.testng.Assert;

public class AutoStackPage {
    static By AUTOSTACK_PAGE_TITLE = By
            .xpath("html/body/div[1]/section/div/h1");
    static By AUTOSTACK_PAGE_HELP_TEXT_1 = By
            .xpath("html/body/div[1]/section/div/ul/li[1]");
    static By AUTOSTACK_PAGE_HELP_TEXT_3 = By
            .xpath("html/body/div[1]/section/div/ul/li[2]/ul/li[1]");
    static By AUTOSTACK_PAGE_HELP_TEXT_4 = By
            .xpath("html/body/div[1]/section/div/ul/li[2]/ul/li[2]");
    static By AUTOSTACK_PAGE_HELP_TEXT_5 = By
            .xpath("html/body/div[1]/section/div/ul/li[3]");
    static By AUTOSTACK_PAGE_FORM_TITLE = By
            .xpath("html/body/div[1]/section/div/section/div[2]/h3");
    static By AUTOSTACK_PAGE_REGION_LABEL = By.xpath("//fieldset/div[1]/label");
    static By AUTOSTACK_PAGE_GROUP_LABEL = By.xpath("//fieldset/div[2]/label");
    static By AUTOSTACK_PAGE_AWS_TAG_LABEL = By
            .xpath("//fieldset/div[3]/label");
    static By AUTOSTACK_PAGE_AWS_FORM_HELP_TEXT = By
            .xpath("//span[@class='help-block']");
    static By AUTOSTACK_PAGE_WILDCARD_LINK = By
            .xpath("//span[@class='help-block']/a");
    static By EXAMPLE_TEXT = By.xpath("//fieldset/div[3]/div/span/strong");
    static By EXAMPLE = By.xpath("//fieldset/div[3]/div/span/code");
    static By UNIQUE_NAME_OF_GROUP_TEXT_BOX = By.id("name");
    static By AWS_TAG_FILTER_TEXT_BOX = By.id("tags");
    static By AUTOSTACK_PAGE_FINDMEMBER_BUTTON = By
            .xpath("//button[@id='begin']");
    static By NAVIGATE_TO_BROWSE_PAGE = By
            .xpath("//a[@href='/YOMP/instances/manual']");
    static By AUTOSTACK_PAGE_CREATE_BUTTON = By
            .xpath("html/body/div[3]/div/div/div[3]/button[2]");
    static By NAVIGATE_TO_IMPORT_PAGE = By
            .xpath("//a[@href='/YOMP/instances/import']");
    static By OPEN_MANAGE_DROPDOWN = By
            .xpath("//li[@class='setup dropdown']/a/span[2]");
    static By AUTOSTACK_CREATED = By
            .linkText("test_autostack (YOMP Autostack)");
    static By NAVIGATE_TO_CUSTOM_METRIC_PAGE = By
            .xpath("//a[@href='/YOMP/custom']");
    static int WAIT_TIME = 10;

    public static void autoStackPageTitleVerification(WebDriver driver) {
        String autoStackPageTitle = driver.findElement(AUTOSTACK_PAGE_TITLE)
                .getText();
        Assert.assertEquals(autoStackPageTitle, "Select Autostacks");
    }

    public static void autoStackPageHelpTextVerification(WebDriver driver) {
        String autoStackPageHelpText1 = driver.findElement(
                AUTOSTACK_PAGE_HELP_TEXT_1).getText();
        String autoStackPageHelpText3 = driver.findElement(
                AUTOSTACK_PAGE_HELP_TEXT_3).getText();
        String autoStackPageHelpText4 = driver.findElement(
                AUTOSTACK_PAGE_HELP_TEXT_4).getText();
        String autoStackPageHelpText5 = driver.findElement(
                AUTOSTACK_PAGE_HELP_TEXT_5).getText();
        Assert.assertEquals(
                autoStackPageHelpText1,
                "Create a group of logically related EC2 instances that will be monitored as a single \"Instance\" within YOMP");
        Assert.assertEquals(autoStackPageHelpText3, "Be in the same AWS Region");
        Assert.assertEquals(autoStackPageHelpText4,
                "Have been previously tagged in AWS");
        Assert.assertEquals(autoStackPageHelpText5,
                "You must give this group a unique name");
    }

    public static void autoStackPageFormVerification(WebDriver driver) {
        String autoStackPageTitleVerification = driver.findElement(
                AUTOSTACK_PAGE_FORM_TITLE).getText();
        Assert.assertEquals(autoStackPageTitleVerification,
                "Create a Group by AWS Tag and Monitor the Group");
    }

    public static void autoStackPageFormLabelVerification(WebDriver driver) {
        String autoStackPageFormLabel1 = TestUtilities.waitGetText(
                AUTOSTACK_PAGE_REGION_LABEL, driver, WAIT_TIME);
        String autoStackPageFormLabel2 = TestUtilities.waitGetText(
                AUTOSTACK_PAGE_GROUP_LABEL, driver, WAIT_TIME);
        String autoStackPageFormLabel3 = TestUtilities.waitGetText(
                AUTOSTACK_PAGE_AWS_TAG_LABEL, driver, WAIT_TIME);
        Assert.assertEquals(autoStackPageFormLabel1, "AWS Region");
        Assert.assertEquals(autoStackPageFormLabel2, "Unique Name for Group");
        Assert.assertEquals(autoStackPageFormLabel3, "AWS Tag Filters");
    }

    public static void autoStackPageFormHelpTextVerification(WebDriver driver) {
       String autoStackPageFormWildcardLink = TestUtilities.waitGetText(
                AUTOSTACK_PAGE_WILDCARD_LINK, driver, WAIT_TIME);
        String autoStackPageExampleText = TestUtilities.waitGetText(
                EXAMPLE_TEXT, driver, WAIT_TIME);
        String autoStackPageExample = TestUtilities.waitGetText(EXAMPLE,
                driver, WAIT_TIME);
        Assert.assertEquals(autoStackPageFormWildcardLink, "Wildcards");
        Assert.assertEquals(autoStackPageExampleText, "Example:");
        Assert.assertEquals(autoStackPageExample,
                "Name:*web*,*api* && Env:production*");
    }

    public static void autoStackCreationVerification(WebDriver driver) {
        Select dropdown = new Select(driver.findElement(By.id("region")));
        dropdown.selectByValue("us-west-2");
        driver.findElement(UNIQUE_NAME_OF_GROUP_TEXT_BOX).sendKeys(
                "test_autostack");
        driver.findElement(AWS_TAG_FILTER_TEXT_BOX).sendKeys("*Jenk*");
        TestUtilities.waitClick(AUTOSTACK_PAGE_FINDMEMBER_BUTTON, driver,
                WAIT_TIME);
        TestUtilities
                .waitClick(AUTOSTACK_PAGE_CREATE_BUTTON, driver, WAIT_TIME);
        Assert.assertTrue(driver.findElement(AUTOSTACK_CREATED).isDisplayed(),
                "Autostack not created.");
    }

    public static void autoStackPageTextBoxesVerification(WebDriver driver) {
        Assert.assertTrue(driver.findElement(UNIQUE_NAME_OF_GROUP_TEXT_BOX)
                .isDisplayed(), "Unique name for group textbox not present");
        Assert.assertTrue(driver.findElement(AWS_TAG_FILTER_TEXT_BOX)
                .isDisplayed(), "AWS tag filter textbox not present");
    }

    public static void autoStackPageButtonVerification(WebDriver driver) {
        String autoStackPageFindMemberButton = TestUtilities.waitGetText(
                AUTOSTACK_PAGE_FINDMEMBER_BUTTON, driver, WAIT_TIME);
        ReusableTests.testDoneButtonVerification(driver);
        Assert.assertEquals(autoStackPageFindMemberButton, "Find Members");
    }

    public static void autoStackPageColumnVerification(WebDriver driver) {
        ReusableTests
                .testInstancesCurrentlyMonitoredByYOMPTitleVerification(driver);
        ReusableTests
                .testInstancesCurrentlyMonitoredByYOMPColumnNamesVerification(driver);
    }

    public static void autoStackPageHeader(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testHeaderAfterSetup(driver);
    }

    public static void autoStackPageFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void autoStackPageDoneButtonVerification(WebDriver driver) {
        ReusableTests.testDoneButtonVerification(driver);
    }

    public static void navigateBrowsePage(WebDriver driver) {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        TestUtilities.waitClick(NAVIGATE_TO_BROWSE_PAGE, driver, WAIT_TIME);
    }
}
