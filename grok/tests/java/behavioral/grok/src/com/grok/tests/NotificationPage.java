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
import org.testng.Assert;

public class NotificationPage {
    static By NOTIFICATION_PAGE_TITLE = By.xpath
            (".//*[@id='content']/div/div/h1");
    static By NOTIFICATION_PAGE_CANCEL_BUTTON = By.xpath
            ("//button[@id='back']");
    static By NOTIFICATION_PAGE_SAVE_BUTTON = By.xpath
            ("//button[@id='next']");
    static By NAVIGATE_TO_IMPORT_PAGE = By.xpath
            ("//a[@href='/YOMP/instances/import']");
    static By NOTIFICATION_EMAIL_TEXT_AREA = By.xpath(".//*[@id='sender']");
    static By NOTIFICATION_LABEL_NOTIFICATION_EMAIL = By.xpath
            (".//*[@id='content']/div/div/form/fieldset/div[1]/label");
    static By NOTIFICATION_LABEL_AWS_REGION = By.xpath
            ("//label[@for='region']");
    static By NAVIGATE_TO_CUSTOM_METRIC_PAGE = By.xpath
            ("//a[@href='/YOMP/custom']");
    static By OPEN_MANAGE_DROPDOWN = By.xpath
            ("//li[@class='setup dropdown']/a/span[2]");
    static By NOTIFICATION_HELP_TEXT_1 = By.xpath
            (".//*[@id='content']/div/div/ul/li[1]");
    static By NOTIFICATION_LINK = By.xpath
            (".//*[@id='content']/div/div/ul/li[2]/a");
    static By NOTIFICATION_HELP_TEXT_3 = By.xpath
            (".//*[@id='content']/div/div/ul/li[3]");
    static By NOTIFICATION_HELP_TEXT_4 = By.xpath
            (".//*[@id='content']/div/div/ul/li[4]");
    static By NOTIFICATION_HELP_TEXT_5 = By.xpath
            (".//*[@id='content']/div/div/ul/li[5]");
    static int WAIT_TIME = 10;

    public static void notificationPageTitleVerification(WebDriver driver) {
        String notificationPageTitle = driver.findElement(NOTIFICATION_PAGE_TITLE)
                .getText();
        Assert.assertEquals(notificationPageTitle, "Notification Settings");
  }

    public static void notificationPageLabelVerification(WebDriver driver) {
        String notificationPageEmailLabel = TestUtilities.waitGetText(
                NOTIFICATION_LABEL_NOTIFICATION_EMAIL, driver, WAIT_TIME);
        String notificationPageRegionLabel = TestUtilities.waitGetText(
                NOTIFICATION_LABEL_AWS_REGION, driver, WAIT_TIME);
        String notificationDefaultEmailID = driver.findElement(By.id("sender"))
                .getAttribute("value");
        Assert.assertEquals(notificationPageEmailLabel, "Notification Email");
        Assert.assertEquals(notificationPageRegionLabel, "AWS Region");
        Assert.assertEquals(notificationDefaultEmailID,
                "YOMP-notifications@numenta.com");
  }
    public static void notificationPageHelpTextVerification(WebDriver driver) {
        String notificationHelpText1 = TestUtilities.waitGetText(
                NOTIFICATION_HELP_TEXT_1, driver, WAIT_TIME);
        String notificationHelpLink = TestUtilities.waitGetText(
                NOTIFICATION_LINK, driver, WAIT_TIME);
        String notificationHelpText3 = TestUtilities.waitGetText(
                NOTIFICATION_HELP_TEXT_3, driver, WAIT_TIME);
        String notificationHelpText4 = TestUtilities.waitGetText(
                NOTIFICATION_HELP_TEXT_4, driver, WAIT_TIME);
        String notificationHelpText5 = TestUtilities.waitGetText(
                NOTIFICATION_HELP_TEXT_5, driver, WAIT_TIME);
        Assert.assertEquals(notificationHelpText1,
                "Enter an email address and select a region "
        + "from which notifications will be sent.");
        Assert.assertEquals(notificationHelpLink,
                "Verify your selected email address");
        Assert.assertEquals(notificationHelpText3, "Verify AWS Identity and "
                + "Access Management (IAM) Credentials used to launch this YOMP server have "
                + "'ses:SendEmail' permissions.");
        Assert.assertEquals(notificationHelpText4,
                "If you are not using SES in 'Production' mode, "
        + "you will only be able to send email to verified email addresses and domains.");
        Assert.assertEquals(notificationHelpText5, "SES is region specific, "
        + "so ensure that the region you enter below is the same "
        + "as that of the sender email/domain.");
    }

    public static void notificationPageButtonVerification(WebDriver driver) {
        String notificationPageCancelButton = TestUtilities.waitGetText(
                NOTIFICATION_PAGE_CANCEL_BUTTON, driver, WAIT_TIME);
        String notificationPageSaveButton = TestUtilities.waitGetText(
                NOTIFICATION_PAGE_SAVE_BUTTON, driver, WAIT_TIME);
        Assert.assertEquals(notificationPageCancelButton, "Cancel");
        Assert.assertEquals(notificationPageSaveButton, "Save");
    }

    public static void notificationPageHeader(WebDriver driver)
      throws InterruptedException {
        ReusableTests.testHeaderAfterSetup(driver);
    }

    public static void notificationPageFooter(WebDriver driver)
      throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void navigateCustomMetric(WebDriver driver)
      throws InterruptedException {
        TestUtilities.waitClick(OPEN_MANAGE_DROPDOWN, driver, WAIT_TIME);
        TestUtilities.waitClick(NAVIGATE_TO_CUSTOM_METRIC_PAGE, driver,
                WAIT_TIME);
    }
}
