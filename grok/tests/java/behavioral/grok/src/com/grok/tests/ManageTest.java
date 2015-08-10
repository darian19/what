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

import java.util.List;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.Select;
import org.testng.Assert;

public class ManageTest {
    static By MANAGE_PAGE_TITLE = By.xpath("//*[@id='content']/div/div/h1");
    static By MANAGE_PAGE_SUBTITLE = By
            .xpath("//div[@id='instance-list']/div/h3");
    static By MANAGE_PAGE_BUTTON = By
            .xpath("//button[@data-toggle='dropdown']");
    static By MANAGE_PAGE_WEB_PAGE_SECTION_TITLE = By
            .xpath("//div[@class='YOMP-embed-form YOMP-panel well']/h3");
    static By MANAGE_PAGE_WIDTH_INPUT = By.xpath("//input[@id='domain']");
    static By MONITORED_ADDITIONAL_INSTANCES_BUTTON = By
            .xpath("//button[@data-toggle='dropdown']");
    static By MANAGE_ADD_YOMP_TITLE = By
            .xpath("//div[@class='YOMP-embed-form YOMP-panel well']/h3");
    static By MANAGE_ADD_YOMP_HELP_TEXT_TITLE = By
            .xpath("//div[@class='YOMP-embed-form YOMP-panel well']/p");
    /*
     * Each of MANAGE_ADD_YOMP_HELP_TEXT_# / is one of the help text bullet
     * points present under "Add YOMP to Any Web Page" section in the /YOMP
     * page.
     */
    static By MANAGE_ADD_YOMP_HELP_TEXT_1 = By
            .xpath("//div[@class='YOMP-embed-form YOMP-panel well']/ul/li[1]");
    static By MANAGE_ADD_YOMP_HELP_TEXT_2 = By
            .xpath("//div[@class='YOMP-embed-form YOMP-panel well']/ul/li[2]");
    static By MANAGE_HOST_NAME = By
            .xpath("//form[@id='form']/fieldset/div[1]/label");
    static By MANAGE_WIDTH = By
            .xpath("//form[@id='form']/fieldset/div[2]/label");
    static By MANAGE_HEIGHT = By
            .xpath("//form[@id='form']/fieldset/div[3]/label");
    static By MANAGE_EMBEDCODE = By.xpath("id('form')/x:div[1]/x:div/x:label");
    static By MANAGE_HOST_NAME_TEXT_BOX = By.xpath("//input[@id='domain']");
    static By MANAGE_WIDTH_TEXT_BOX = By.xpath("//input[@id='width']");
    static By MANAGE_HEIGHT_TEXT_BOX = By.xpath("//input[@id='height']");
    static By MANAGE_EMBEDCODE_TEXT_BOX = By.xpath("//textarea[@id='code']");
    static By OPEN_MANAGE_DROPDOWN = By
            .xpath("//li[@class='setup dropdown']/a/span[2]");
    static By ALLOW_TECH_SUPPORT_ACCESS = By
            .xpath(".//*[@id='support-access-enable']");
    static By REVOKE_TECH_SUPPORT_ACCESS = By
            .xpath(".//*[@id='support-access-disable']");
    static By NAVIGATE_TO_AUTOSTACK_PAGE = By
            .xpath("//a[@href='/YOMP/instances/autostack']");
    static By NAVIGATE_TO_SBNT_PAGE = By
            .xpath("//a[@href='/YOMP/instances/auto']");
    static By FIND_MEMBERS_BUTTON = By.id("begin");
    static By OK_BUTTON = By.xpath("html/body/div[3]/div/div/div[3]/button[2]");
    static int WAIT_TIME = 20;

    public static void manageTitleVerification(WebDriver driver) {
        String managePagetitle = TestUtilities.waitGetText(MANAGE_PAGE_TITLE,
                driver, WAIT_TIME);
        Assert.assertEquals(managePagetitle, "Manage Monitored Instances");
    }

    public static void allowTechSupportAccess(WebDriver driver) {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        String allowTechSupportAccessText = TestUtilities.waitGetText(
                ALLOW_TECH_SUPPORT_ACCESS, driver, WAIT_TIME);
        Assert.assertEquals(allowTechSupportAccessText,
                "Allow Tech Support Access");
        TestUtilities.waitClick(ALLOW_TECH_SUPPORT_ACCESS, driver, WAIT_TIME);
    }

    public static void revokeTechSupportAccess(WebDriver driver) {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        String revokeTechSupportAccessText = TestUtilities.waitGetText(
                REVOKE_TECH_SUPPORT_ACCESS, driver, WAIT_TIME);
        Assert.assertEquals(revokeTechSupportAccessText,
                "Revoke Tech Support Access");
        TestUtilities.waitClick(REVOKE_TECH_SUPPORT_ACCESS, driver, WAIT_TIME);
    }

    public static void manageInstancesCurrentlyMonitoredByYOMPSectionVerification(
            WebDriver driver) {
        ReusableTests
                .testInstancesCurrentlyMonitoredByYOMPTitleVerification(driver);
        ReusableTests
                .testInstancesCurrentlyMonitoredByYOMPColumnNamesVerification(driver);
    }

    public static void monitorAdditionalInstancesDropDownVerification(
            WebDriver driver) {
        String managePageDropDown = TestUtilities.waitGetText(
                MONITORED_ADDITIONAL_INSTANCES_BUTTON, driver, WAIT_TIME);
        Assert.assertEquals(managePageDropDown, "Monitor Additional Instances");
    }

    public static void addYOMPToWebPageTitleVerification(WebDriver driver) {
        String managePageYOMPToWebPageTitle = TestUtilities.waitGetText(
                MANAGE_ADD_YOMP_TITLE, driver, WAIT_TIME);
        Assert.assertEquals(managePageYOMPToWebPageTitle,
                "Add YOMP to Any Web Page");
    }

    public static void YOMPToWebPageHelpTextVerification(WebDriver driver) {
        String managePageYOMPToWebPageTitle = TestUtilities.waitGetText(
                MANAGE_ADD_YOMP_HELP_TEXT_TITLE, driver, WAIT_TIME);
        /*
         * 1st bullet point Add YOMP to Any Web Page section
         * "i.e. Enter the hostname where you will embed the widget, and the width and height."
         */
        String managePageYOMPToWebPageHelpText1 = TestUtilities.waitGetText(
                MANAGE_ADD_YOMP_HELP_TEXT_1, driver, WAIT_TIME);
        /*
         * 2st bullet point Add YOMP to Any Web Page section
         * "i.e. Copy the Embed Code, and place it in the HTML source code of your website."
         */
        String managePageYOMPToWebPageHelpText2 = TestUtilities.waitGetText(
                MANAGE_ADD_YOMP_HELP_TEXT_2, driver, WAIT_TIME);
        Assert.assertEquals(managePageYOMPToWebPageHelpText1,
                "Enter the hostname where you will embed the widget, "
                        + "and the width and height.");
        Assert.assertEquals(managePageYOMPToWebPageTitle,
                "To place a YOMP Charts dashboard widget on your web page:");
        Assert.assertEquals(managePageYOMPToWebPageHelpText2,
                "Copy the Embed Code, and place it in the HTML "
                        + "source code of your website.");
    }

    public static void YOMPToWebPageLabelVerification(WebDriver driver) {
        String managePageHostnameLabel = TestUtilities.waitGetText(
                MANAGE_HOST_NAME, driver, WAIT_TIME);
        String managePageWidthLabel = TestUtilities.waitGetText(MANAGE_WIDTH,
                driver, WAIT_TIME);
        String managePageHeightLabel = TestUtilities.waitGetText(MANAGE_HEIGHT,
                driver, WAIT_TIME);
        String managePageEmbedcodeLabel = TestUtilities.waitGetText(
                MANAGE_EMBEDCODE, driver, WAIT_TIME);
        Assert.assertEquals(managePageHostnameLabel, "Destination Hostname");
        Assert.assertEquals(managePageWidthLabel, "Width");
        Assert.assertEquals(managePageHeightLabel, "Height");
        Assert.assertEquals(managePageEmbedcodeLabel, "Embed Code");
    }

    public static void manageTextBoxesVerification(WebDriver driver) {
        Assert.assertTrue(driver.findElement(MANAGE_HOST_NAME_TEXT_BOX)
                .isDisplayed(), "hostnameTextbox not present");
        Assert.assertTrue(driver.findElement(MANAGE_WIDTH_TEXT_BOX)
                .isDisplayed(), "widthtextBox not present");
        Assert.assertTrue(driver.findElement(MANAGE_HEIGHT_TEXT_BOX)
                .isDisplayed(), "heightTexBox not present");
        Assert.assertTrue(driver.findElement(MANAGE_EMBEDCODE_TEXT_BOX)
                .isDisplayed(), "embedCodeTextBox not present");
    }

    public static void manageHeader(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testHeaderAfterSetup(driver);
    }

    public static void manageFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void testDropDown(WebDriver driver) {
        String[] hrefArray = { "manual", "auto", "import", "autostack",
                "custom" };
        List<WebElement> anchors = driver.findElements(By
                .cssSelector("div div ul li a"));
        Assert.assertTrue(hrefArray.length == anchors.size());
        for (int i = 0; i < anchors.size(); i++) {
            String hrefString = anchors.get(i).getAttribute("href").toString();
            Assert.assertTrue(hrefString.contains(hrefArray[i]),
                    String.format("%s not present", hrefString));
        }
    }

    public static void manageExportRemoveCheckAfterAddingInstances(
            WebDriver driver) {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        // Navigation and creating autostack to assert export and import button
        // after adding instances.
        TestUtilities.waitClick(NAVIGATE_TO_AUTOSTACK_PAGE, driver, WAIT_TIME);
        Select dropdown = new Select(driver.findElement(By.id("region")));
        dropdown.selectByValue("us-west-2");
        driver.findElement(By.id("name")).sendKeys("test");
        driver.findElement(By.id("tags")).sendKeys("*Jenk*");
        TestUtilities.waitClick(FIND_MEMBERS_BUTTON, driver, WAIT_TIME);
        TestUtilities.waitClick(OK_BUTTON, driver, WAIT_TIME);
        driver.navigate().back();
        ReusableTests.testRemoveButtonVerfication(driver);
        ReusableTests.testExportButtonVerfication(driver);
    }

    // We are navigating to "Search by name tag" page for further checks of the
    // respective page.
   public static void navigateSBNTPage(WebDriver driver)
            throws InterruptedException {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        TestUtilities.waitClick(NAVIGATE_TO_SBNT_PAGE, driver, WAIT_TIME);
    }
}
