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
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.Assert;
import org.testng.annotations.Test;

public class RegistrationTest {
    /*
     * Each of AUTH_HELP_TEXT_# / registrationPageHelpText1 is one of the bullet
     * points from the in the /register page.
     */
    static By REGISTRATION_FORM_TITLE = By
            .xpath("//*[@id='content']/div/div/h1");
    static By REGISTRATION_SUB_TITLE = By.xpath("//*[@id='content']/div/div/p");
    static By REGISTRATION_HELP_TEXT_1 = By
            .xpath("//span[@class='help-block']/ul/li[1]");
    static By REGISTRATION_HELP_TEXT_2 = By
            .xpath("//span[@class='help-block']/ul/li[2]");
    static By REGISTRATION_TEXTBOX_YOUR_NAME = By.id("name");
    static By REGISTRATION_TEXTBOX_COMPANY = By.xpath("//input[@id='company']");
    static By REGISTRATION_TEXTBOX_EMAIL = By.id("email");
    static By REGISTRATION_ARTICLE = By
            .xpath("//article/p[@class='strong text-center']");
    static By REGISTRATION_AUTHORIZE_CHECKBOX_TEXT = By
            .xpath("//div[@class='form-group']/div[1]/label");
    static By REGISTRATION_ACCEPT_CHECKBOX_TEXT = By
            .xpath("//div[@class='form-group']/div[2]/label");
    static By REGISTRATION_LABEL_YOUR_NAME = By.xpath("//label[@for='name']");
    static By REGISTRATION_LABEL_COMPANY = By.xpath("//label[@for='company']");
    static By REGISTRATION_LABEL_EMAIL = By.xpath("//label[@for='email']");
    static By REGISTRATION_BUTTON_BACK = By.xpath("//button[@id='back']");
    static By REGISTRATION_BUTTON_NEXT = By.xpath("//button[@id='next']");
    static By REGISTRATION_ACCEPT_CHECKBOX = By
            .xpath("//div[@class='form-group']/div[2]/label/input");
    static By REGISTRATION_AUTHORIZE_CHECKBOX = By
            .xpath("//div[@class='form-group']/div[1]/label/input");
    static By REGISTRATION_INVALID_EMAIL = By
            .xpath("//div[@class='bootbox-body']/div");
    static By REGISTRATION_OK_BUTTON = By
            .xpath("//button[@data-bb-handler='ok']");
    static By REGISTRATION_SETUP_PROGRESS = By
            .xpath("//div[@class='text-muted']/span");
    static By REGISTRATION_SAVE_DISABLED = By
            .xpath("//button[@disabled='disabled']");
    static int WAIT_TIME = 10;

    public static void registrationTitleVerification(WebDriver driver) {
        String registerPageTitle = TestUtilities.waitGetText(
                REGISTRATION_FORM_TITLE, driver, WAIT_TIME);
        String registrationPageSubTitle = TestUtilities.waitGetText(
                REGISTRATION_SUB_TITLE, driver, WAIT_TIME);
        Assert.assertEquals(registerPageTitle, "Step 1: Registration and Terms");
        Assert.assertEquals(registrationPageSubTitle,
                "Please register (optional):");
    }

    public static void registrationsHeader(WebDriver driver) throws Exception {
        ReusableTests.testHeaderDuringSetup(driver);
    }

    public static void registrationsFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void registrationHeadingHelpTextVerification(WebDriver driver) {
        /*
         * 1st bullet point :
         * "Step 2: We will use your email to send you release updates or product info"
         */
        String registrationPageHelpText1 = TestUtilities.waitGetText(
                REGISTRATION_HELP_TEXT_1, driver, WAIT_TIME);
        /* 2nd bullet point : "We do not sell or share email addresses" */
        String registrationPageHelpText2 = TestUtilities.waitGetText(
                REGISTRATION_HELP_TEXT_2, driver, WAIT_TIME);
        Assert.assertEquals(registrationPageHelpText1,
                "We will use your email to send you release updates or product info.");
        Assert.assertEquals(registrationPageHelpText2,
                "We do not sell or share email addresses.");
    }

    public static void registrationLabelVerification(WebDriver driver) {
        String registrationPageNameYourNameLabel = TestUtilities.waitGetText(
                REGISTRATION_LABEL_YOUR_NAME, driver, WAIT_TIME);
        String registrationPageNameCompanyLabel = TestUtilities.waitGetText(
                REGISTRATION_LABEL_COMPANY, driver, WAIT_TIME);
        String registrationPageNameWorkEmailLabel = TestUtilities.waitGetText(
                REGISTRATION_LABEL_EMAIL, driver, WAIT_TIME);
        String registrationPageNameAgreementLabel = TestUtilities.waitGetText(
                REGISTRATION_ARTICLE, driver, WAIT_TIME);
        Assert.assertEquals(registrationPageNameYourNameLabel, "Your Name");
        Assert.assertEquals(registrationPageNameCompanyLabel, "Company");
        Assert.assertEquals(registrationPageNameWorkEmailLabel, "Work Email");
        Assert.assertEquals(registrationPageNameAgreementLabel,
                "SOFTWARE LICENSE AGREEMENT");
    }

    public static void registrationButtonVerification(WebDriver driver) {
        String registrationPageNextButton = TestUtilities.waitGetText(
                REGISTRATION_BUTTON_NEXT, driver, WAIT_TIME);
        String registrationPageBackButton = TestUtilities.waitGetText(
                REGISTRATION_BUTTON_BACK, driver, WAIT_TIME);
        Assert.assertEquals(registrationPageNextButton, "Next");
        Assert.assertEquals(registrationPageBackButton, "Back");
    }

    public static void registrationCheckboxVerification(WebDriver driver) {
        String registrationPageAuthorizeCheckBox = TestUtilities.waitGetText(
                REGISTRATION_AUTHORIZE_CHECKBOX_TEXT, driver, WAIT_TIME);
        String registrationPageAcceptCheckBox = TestUtilities.waitGetText(
                REGISTRATION_ACCEPT_CHECKBOX_TEXT, driver, WAIT_TIME);
        Assert.assertEquals(registrationPageAuthorizeCheckBox,
                "I authorize the collection of anonymous "
                        + "usage statistics to improve YOMP.");
        Assert.assertEquals(registrationPageAcceptCheckBox,
                "I accept the YOMP Software License Agreement.");
    }

    public static void registrationInvalidEmailIdVerification(WebDriver driver)
            throws Exception {
        driver.findElement(REGISTRATION_TEXTBOX_EMAIL).sendKeys("InvalidEmail");
        TestUtilities.waitClick(REGISTRATION_BUTTON_NEXT, driver, WAIT_TIME);
        String registrationPageInvalidEmailMessage = TestUtilities.waitGetText(
                REGISTRATION_INVALID_EMAIL, driver, WAIT_TIME);
        Assert.assertEquals(registrationPageInvalidEmailMessage,
                "Invalid email address.");
        TestUtilities.waitClick(REGISTRATION_OK_BUTTON, driver, WAIT_TIME);
    }

    // TODO
    /*
     * Below test is skipped because of MER-2978 "([WEB] Invalid email //
     * address x@y appears to be successful)" is not fixed yet, Once its fixed
     * we can remove the @Test(enabled = false annotation) from here.
     */
    @Test(enabled = false)
    public static void registrationInvalidEmailIdVerification1(WebDriver driver)
            throws Exception {
        driver.findElement(REGISTRATION_TEXTBOX_EMAIL).sendKeys(
                "InvalidEmail@test");
        TestUtilities.waitClick(REGISTRATION_BUTTON_NEXT, driver, WAIT_TIME);
        String registrationPageInvalidEmailMessage = TestUtilities.waitGetText(
                REGISTRATION_INVALID_EMAIL, driver, WAIT_TIME);
        Assert.assertEquals(registrationPageInvalidEmailMessage,
                "Invalid email address.");
        TestUtilities.waitClick(REGISTRATION_OK_BUTTON, driver, WAIT_TIME);
    }

    public static void registrationSetUpProgressBarVerification(WebDriver driver)
            throws Exception {
        ReusableTests.testSetUpProgressText(driver);
    }

    public static void registrationDisabledNextButtonUsingBothCheckBoxes(
            WebDriver driver) throws Exception {
        WebDriverWait wait = new WebDriverWait(driver, WAIT_TIME);
        wait.until(
                ExpectedConditions
                        .presenceOfElementLocated(REGISTRATION_TEXTBOX_EMAIL))
                .clear();
        wait.until(
                ExpectedConditions
                        .presenceOfElementLocated(REGISTRATION_TEXTBOX_YOUR_NAME))
                .sendKeys("John Doe");
        wait.until(
                ExpectedConditions
                        .presenceOfElementLocated(REGISTRATION_TEXTBOX_COMPANY))
                .sendKeys("Numenta");
        wait.until(
                ExpectedConditions
                        .presenceOfElementLocated(REGISTRATION_TEXTBOX_EMAIL))
                .sendKeys("sghatage@numenta.com");
        /*
         * Below scenario is "DE-SELECTING both check-boxes" one by one and then
         * checking the save button is disabled or not.
         */
        TestUtilities
                .waitClick(REGISTRATION_ACCEPT_CHECKBOX, driver, WAIT_TIME);
        Assert.assertFalse(driver.findElement(REGISTRATION_SAVE_DISABLED)
                .isEnabled(), "Next button is enabled");
        TestUtilities.waitClick(REGISTRATION_AUTHORIZE_CHECKBOX, driver,
                WAIT_TIME);
        Assert.assertFalse(driver.findElement(REGISTRATION_SAVE_DISABLED)
                .isEnabled(), "Next button is enabled");
    }

    public static void registrationDisabledNextButtonUsingCheckbox1(
            WebDriver driver) {
        /*
         * Below scenario is "SELECTING" checkbox1" and then checking the save
         * button is disabled or not.
         */
        TestUtilities.waitClick(REGISTRATION_AUTHORIZE_CHECKBOX, driver,
                WAIT_TIME);
        Assert.assertFalse(driver.findElement(REGISTRATION_SAVE_DISABLED)
                .isEnabled(), "Next button is enabled");
        /*
         * Again "de-selecting" the check-box1 to verify further checkbox2
         * scenario.
         */
        TestUtilities.waitClick(REGISTRATION_AUTHORIZE_CHECKBOX, driver,
                WAIT_TIME);
    }

    public static void registrationEnabledNextButtonUsingCheckbox2(
            WebDriver driver) {
        /*
         * Below scenario is "SELECTING checkbox2" and then checking the save
         * button is disabled or not
         */
        TestUtilities
                .waitClick(REGISTRATION_ACCEPT_CHECKBOX, driver, WAIT_TIME);
        Assert.assertTrue(driver.findElement(REGISTRATION_BUTTON_NEXT)
                .isEnabled(), "Next button is not enabled");
        /*
         * Again "de-selecting" the check-box 2 to verify further scenario i.e.
         * enabling of save button when both check-boxes are selected.
         */
        TestUtilities
                .waitClick(REGISTRATION_ACCEPT_CHECKBOX, driver, WAIT_TIME);
    }

    public static void registrationEnabledNextButtonUsingBothCheckboxes(
            WebDriver driver) throws InterruptedException {
        /*
         * Below scenario is "SELECTING both check-boxes" one by one and then
         * checking the save button is disabled or not.
         */
        TestUtilities
                .waitClick(REGISTRATION_ACCEPT_CHECKBOX, driver, WAIT_TIME);
        Assert.assertTrue(driver.findElement(REGISTRATION_BUTTON_NEXT)
                .isEnabled(), "Next button is not enabled");
        TestUtilities.waitClick(REGISTRATION_AUTHORIZE_CHECKBOX, driver,
                WAIT_TIME);
        Assert.assertTrue(driver.findElement(REGISTRATION_BUTTON_NEXT)
                .isEnabled(), "Next button is not enabled");
    }

    public static void registrationNextButtonClick(WebDriver driver) {
        TestUtilities.waitClick(REGISTRATION_BUTTON_NEXT, driver, WAIT_TIME);
    }
}
