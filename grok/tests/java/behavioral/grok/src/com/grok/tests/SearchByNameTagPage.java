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

public class SearchByNameTagPage {
    static By SBNT_FORM_TITLE = By.xpath("html/body/div[1]/section/div/h1");
    static By SBNT_SUB_TITLE = By
            .xpath("html/body/div[1]/section/div/div[2]/div[1]/div/div/h3");
    static By SBNT_TITLE = By.xpath("html/body/div[3]/div/div/div[1]/h4");
    static By SBNT_HELPBLOCK1 = By
            .xpath("html/body/div[1]/section/div/div[2]/div[2]/ul/li[1]");
    static By SBNT_REGION_LABEL = By
            .xpath("html/body/div[1]/section/div/div[2]/div[2]/form/fieldset/div[1]/label");
    static By SBNT_NAME_TAG = By
            .xpath("html/body/div[1]/section/div/div[2]/div[2]/form/fieldset/div[2]/label");
    static By SBNT_NAME_TAG_TEXT_FIELD = By
            .xpath("html/body/div[1]/section/div/div[2]/div[2]/form/fieldset/div[2]/div/input");
    static By SBNT_CONTINUE_BUTTON = By
            .xpath("html/body/div[3]/div/div/div[3]/button[2]");
    static By SBNT_INVALID_REGION = By
            .xpath("html/body/div[3]/div/div/div[2]/div/div");
    static By SBNT_FINDMEMBER_BUTTON = By.xpath("//button[@id='begin'] ");
    static By SBNT_OK_BUTTON = By.xpath("//button[@data-bb-handler='ok']");
    static By SBNT_SETUP_DROPDOWN = By
            .xpath("html/body/header/div/ul/li[3]/ul/li[3]/a");
    static By SBNT_DROPDOWN_DEFAULT = By.xpath("//select//option[1]");
    static By NAVIGATE_TO_IMPORT_PAGE = By
            .xpath("//li[@class='setup dropdown open']/ul/li[4]");
    static By OPEN_MANAGE_DROPDOWN = By
            .xpath("//li[@class='setup dropdown']/a/span[2]");
    static By NAVIGATE_TO_AUTOSTACK_PAGE = By
            .xpath("//a[@href='/YOMP/instances/autostack']");
    static By REMOVE_All_BUTTON = By
            .xpath(".//*[@id='instance-list']/div/form/div/button[2]");
    static By OK_BUTTON = By
            .xpath("html/body/div[3]/div/div/div[3]/button[2]");
    static By CANCEL_BUTTON = By
            .xpath("html/body/div[3]/div/div/div[3]/button[1]");
    static By NO_INSTANCE_FOUND_ERROR_MESSAGE = By
            .xpath("html/body/div[3]/div/div/div[2]/div/p");
    static By OK_ERROR_MESSAGE = By
            .xpath("html/body/div[3]/div/div/div[3]/button");
    static By CROSS_BUTTON = By
            .xpath(".//*[@id='instance-list']/div/form/table/tbody/tr[1]/td[5]/button");
    static int WAIT_TIME = 10;

    /**
     * Helper method to remove instances that were added for monitoring in the
     * "Manage Monitored Instance" page. This is required so that the "Export"
     * and "Remove" button are removed from the "Search By Name Tag" page. Thus
     * the driver can WAIT UNITL the buttons appear again when new instances
     * are added by using the "Search By Name Tag" feature (see
     * sbntExportAndRemoveButtonsVerification). This makes sure that all the
     * tests from this page pass and the driver can navigate to the AutoStack
     * page w/o errors.
     */

    public static void removeInstances(WebDriver driver) {
        TestUtilities.waitClick(REMOVE_All_BUTTON, driver, WAIT_TIME);
        TestUtilities.waitClick(OK_BUTTON, driver, WAIT_TIME);
    }

    public static void cancelRemoveInstances(WebDriver driver) {
        TestUtilities.waitClick(REMOVE_All_BUTTON, driver, WAIT_TIME);
        String cancelButtonText = TestUtilities.waitGetText(CANCEL_BUTTON,
                driver, WAIT_TIME);
        Assert.assertEquals(cancelButtonText, "Cancel");
        TestUtilities.waitClick(CANCEL_BUTTON, driver, WAIT_TIME);
    }

    public static void pageTitleVerification(WebDriver driver) {
        String sbntPageTitle = TestUtilities.waitGetText(SBNT_FORM_TITLE,
                driver, WAIT_TIME);
        Assert.assertEquals(sbntPageTitle, "Search for Instances by Name Tag");
        String sbntSubPageTitle = TestUtilities.waitGetText(SBNT_SUB_TITLE,
                driver, WAIT_TIME);
        Assert.assertEquals(sbntSubPageTitle,
                "Instances Currently Monitored by YOMP");
    }

    public static void headingHelpTextVerification(WebDriver driver) {
        String sbntHelpText1 = TestUtilities.waitGetText(SBNT_HELPBLOCK1,
                driver, WAIT_TIME);
        Assert.assertEquals(sbntHelpText1,
                "Enter an AWS Region and AWS Name Tag to search by.");
    }

    public static void labelVerification(WebDriver driver) {
        String sbntLabel1 = TestUtilities.waitGetText(SBNT_REGION_LABEL,
                driver, WAIT_TIME);
        String sbntLabel2 = TestUtilities.waitGetText(SBNT_NAME_TAG, driver,
                WAIT_TIME);
        Assert.assertEquals(sbntLabel1, "AWS Region");
        Assert.assertEquals(sbntLabel2, "AWS Name Tags");
    }

    public static void errorSelectingRegion(WebDriver driver)
            throws Exception {
        TestUtilities.waitClick(SBNT_FINDMEMBER_BUTTON, driver, WAIT_TIME);
        String invalidRegion = TestUtilities.waitGetText(SBNT_INVALID_REGION,
                driver, WAIT_TIME);
        Assert.assertEquals(invalidRegion,
                "You must select a specific AWS Region");
        TestUtilities.waitClick(SBNT_OK_BUTTON, driver, WAIT_TIME);
    }

    public static void pageSectionTitleVerification(WebDriver driver) {
        ReusableTests
                .testInstancesCurrentlyMonitoredByYOMPTitleVerification(driver);
    }

    public static void columnVerification(WebDriver driver) {
        ReusableTests
                .testInstancesCurrentlyMonitoredByYOMPColumnNamesVerification(driver);
    }

    public static void header(WebDriver driver) throws InterruptedException {
        ReusableTests.testHeaderAfterSetup(driver);
    }

    public static void footer(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void selectingInstances(WebDriver driver)
            throws Exception {
        Select dropdown = new Select(driver.findElement(By.id("region")));
        dropdown.selectByValue("us-west-2");
        driver.findElement(SBNT_NAME_TAG_TEXT_FIELD).sendKeys("*jenkin*");
        TestUtilities.waitClick(SBNT_FINDMEMBER_BUTTON, driver, WAIT_TIME);
        TestUtilities.waitClick(SBNT_CONTINUE_BUTTON, driver, WAIT_TIME);
    }

    public static void selectInstanceWithRegionWithoutTagName(
        WebDriver driver) throws Exception {
        Select dropdown = new Select(driver.findElement(By.id("region")));
        dropdown.selectByValue("ap-southeast-1");
        driver.findElement(SBNT_NAME_TAG_TEXT_FIELD).sendKeys("*jenkin*");
        TestUtilities.waitClick(SBNT_FINDMEMBER_BUTTON, driver, WAIT_TIME);
        String noInstanceFoundErrorMessageText = TestUtilities.waitGetText(
                NO_INSTANCE_FOUND_ERROR_MESSAGE, driver, WAIT_TIME);
        Assert.assertEquals(noInstanceFoundErrorMessageText,
                "Sorry! A problem was encountered. Please try again.");
        TestUtilities.waitClick(OK_ERROR_MESSAGE, driver, WAIT_TIME);
        driver.findElement(SBNT_NAME_TAG_TEXT_FIELD).clear();
    }

    public static void removeInstanceByClickingCrossButton(WebDriver driver)
            throws Exception {
        TestUtilities.waitClick(CROSS_BUTTON, driver, WAIT_TIME);
        TestUtilities.waitClick(OK_BUTTON, driver, WAIT_TIME);
    }

    public static void exportAndRemoveButtonsVerification(WebDriver driver) {
        ReusableTests.testRemoveButtonVerfication(driver);
        ReusableTests.testExportButtonVerfication(driver);
    }

    public static void navigateAutoStack(WebDriver driver) {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        TestUtilities.waitClick(NAVIGATE_TO_AUTOSTACK_PAGE, driver, WAIT_TIME);
    }
}
