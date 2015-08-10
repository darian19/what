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

import java.io.FileNotFoundException;
import java.io.IOException;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

import org.testng.Assert;

public class AuthTest {

    /*
     * Each of AUTH_HELP_TEXT_# / authPageHelpText1 is one of the bullet points
     * from the "Step 2: Enter AWS Credentials" in the /auth page.
     */
    static By AUTH_HELP_TEXT_1 = By
            .xpath("//div[@class='col-md-8 col-md-offset-2']/ul/li[1]");
    static By AUTH_HELP_TEXT_2 = By
            .xpath("//div[@class='col-md-8 col-md-offset-2']/ul/li[2]");
    static By AUTH_HELP_TEXT_3 = By
            .xpath("//div[@class='col-md-8 col-md-offset-2']/ul/li[3]");
    static By AUTH_HELP_TEXT_4 = By
            .xpath("//div[@class='col-md-8 col-md-offset-2']/ul/li[4]");
    static By AUTH_LINK = By
            .xpath("//div[@class='col-md-8 col-md-offset-2']/ul/li[2]/a");
    static By ACCESS_KEY_TEXTBOX = By.xpath("//*[@id='key']");
    static By SECRET_KEY_TEXTBOX = By.xpath("//*[@id='secret']");
    static By AUTH_BUTTON_BACK = By.xpath("//button[@id='back']");
    static By AUTH_BUTTON_NEXT = By.xpath("//button[@id='next']");
    static By AUTH_FORM_TITLE = By.xpath(".//*[@id='content']/div/div/h1");
    static By AUTH_SETUP_PROGRESS = By.xpath("//div[@class='text-muted']/span");
    static By AUTH_LABEL_ACCESS_KEY = By.xpath("//label[@for='key']");
    static By AUTH_LABEL_SECRET_KEY = By.xpath("//label[@for='secret']");
    static By AUTH_INVALID_CREDENTIALS = By
            .xpath("//div[@class='bootbox-body']/div");
    static By AUTH_OK_BUTTON = By.xpath("//button[@data-bb-handler='ok']");
    static int WAIT_TIME = 10;

    public static void authHelpTextVerification(WebDriver driver) {
        /* 1st bullet point under "Step 2: Enter AWS Credentials" */
        String authPageHelpText1 = TestUtilities.waitGetText(AUTH_HELP_TEXT_1,
                driver, WAIT_TIME);
        /* 2nd bullet point under "Step 2: Enter AWS Credentials */
        String authPageHelpText2 = TestUtilities.waitGetText(AUTH_HELP_TEXT_2,
                driver, WAIT_TIME);
        /* 3rd bullet point under "Step 2: Enter AWS Credentials" */
        String authPageHelpText3 = TestUtilities.waitGetText(AUTH_HELP_TEXT_3,
                driver, WAIT_TIME);
        /* 4th bullet point under "Step 2: Enter AWS Credentials" */
        String authPageHelpText4 = TestUtilities.waitGetText(AUTH_HELP_TEXT_4,
                driver, WAIT_TIME);

        String authLink = TestUtilities.waitGetText(AUTH_LINK, driver,
                WAIT_TIME);
        Assert.assertEquals(authPageHelpText1,
                "Your credentials will be used to access "
                        + "read-only Cloudwatch metric data.");
        Assert.assertEquals(authPageHelpText2,
                "Follow these directions to create a new AWS IAM user "
                        + "with read-only permissions.");
        Assert.assertEquals(authPageHelpText4,
                "Your credentials are private and safe, and will not be stored "
                        + "outside of your server instance.");
        Assert.assertEquals(authPageHelpText3,
                "Alternatively, you can use an existing AWS IAM user"
                        + " with read-access premissions.");
        Assert.assertEquals(authLink, "Follow these directions");
    }

    public static void authTitleVerification(WebDriver driver) {
        String authPageTitle = TestUtilities.waitGetText(AUTH_FORM_TITLE,
                driver, WAIT_TIME);
        Assert.assertEquals(authPageTitle, "Step 2: Enter AWS Credentials");
    }

    public static void authLabelVerification(WebDriver driver) {
        String authAccessKeyLabel = TestUtilities.waitGetText(
                AUTH_LABEL_ACCESS_KEY, driver, WAIT_TIME);
        String authSecretKeyLabel = TestUtilities.waitGetText(
                AUTH_LABEL_SECRET_KEY, driver, WAIT_TIME);
        Assert.assertEquals(authAccessKeyLabel, "Access Key ID");
        Assert.assertEquals(authSecretKeyLabel, "Secret Key");
    }

    public static void authButtonVerification(WebDriver driver) {
        String authNextButton = TestUtilities.waitGetText(AUTH_BUTTON_NEXT,
                driver, WAIT_TIME);
        String authBackButton = TestUtilities.waitGetText(AUTH_BUTTON_BACK,
                driver, WAIT_TIME);
        Assert.assertEquals(authNextButton, "Next");
        Assert.assertEquals(authBackButton, "Back");
    }

    public static void authHeader(WebDriver driver) throws InterruptedException {
        ReusableTests.testHeaderDuringSetup(driver);
    }

    public static void authFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void authSetUpProgressBarVerification(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testSetUpProgressText(driver);
    }

    public static void authInvalidCredentialIdVerification(WebDriver driver)
            throws Exception {
        driver.findElement(ACCESS_KEY_TEXTBOX).sendKeys("Invalidusername");
        driver.findElement(SECRET_KEY_TEXTBOX).sendKeys("Invalidpassword");
        TestUtilities.waitClick(AUTH_BUTTON_NEXT, driver, WAIT_TIME);
        String invalidAwscredential = TestUtilities.waitGetText(
                AUTH_INVALID_CREDENTIALS, driver, WAIT_TIME);
        Assert.assertEquals(invalidAwscredential,
                "AWS was not able to validate the provided access credentials");
        TestUtilities.waitClick(AUTH_OK_BUTTON, driver, WAIT_TIME);
    }

    public static void authValidAccessKeyIDInvalidSecretKeyVerification(
            String accessKeyID, WebDriver driver) {
        driver.findElement(ACCESS_KEY_TEXTBOX).sendKeys(accessKeyID);
        driver.findElement(SECRET_KEY_TEXTBOX).sendKeys("Invalidpassword");
        TestUtilities.waitClick(AUTH_BUTTON_NEXT, driver, WAIT_TIME);
        String invalidAwscredential = TestUtilities.waitGetText(
                AUTH_INVALID_CREDENTIALS, driver, WAIT_TIME);
        Assert.assertEquals(invalidAwscredential,
                "AWS was not able to validate the provided "
                        + "secret access credential.");
        TestUtilities.waitClick(AUTH_OK_BUTTON, driver, WAIT_TIME);
        driver.findElement(ACCESS_KEY_TEXTBOX).clear();
        driver.findElement(SECRET_KEY_TEXTBOX).clear();
    }

    public static void authInvalidAccessKeyIDValidSecretKeyVerification(
            String secretKey, WebDriver driver) {
        driver.findElement(ACCESS_KEY_TEXTBOX).sendKeys("Invalidusername");
        driver.findElement(SECRET_KEY_TEXTBOX).sendKeys(secretKey);
        TestUtilities.waitClick(AUTH_BUTTON_NEXT, driver, WAIT_TIME);
        String invalidAwscredential = TestUtilities.waitGetText(
                AUTH_INVALID_CREDENTIALS, driver, WAIT_TIME);
        Assert.assertEquals(invalidAwscredential,
                "AWS was not able to validate the provided access credentials");
        TestUtilities.waitClick(AUTH_OK_BUTTON, driver, WAIT_TIME);
        driver.findElement(ACCESS_KEY_TEXTBOX).clear();
        driver.findElement(SECRET_KEY_TEXTBOX).clear();
    }

    public static void typeAccessKeyID(String accessKeyID, WebDriver driver)
            throws FileNotFoundException, IOException {
        Assert.assertTrue(driver.findElement(ACCESS_KEY_TEXTBOX).isDisplayed(),
                "usernamelocator textbox not present");
        driver.findElement(ACCESS_KEY_TEXTBOX).sendKeys(accessKeyID);
    }

    public static void typeSecretKey(String secretKey, WebDriver driver)
            throws FileNotFoundException, IOException {
        Assert.assertTrue(driver.findElement(SECRET_KEY_TEXTBOX).isDisplayed(),
                "passwordlocator textbox not present");
        driver.findElement(SECRET_KEY_TEXTBOX).sendKeys(secretKey);
    }

    public static void submitLogin(WebDriver driver) {
        ReusableTests.testSubmitLogin(driver);
    }
}
