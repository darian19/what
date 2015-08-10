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

import org.testng.Assert;

public class WelcomeTest {
    static By WELCOME_FORMTITLE = By.xpath(".//*[@id='welcome']/div[1]/h1");
    /*
     * Locators for each of WELCOME_HELP_TEXT_# / welcomePageHelpText# locator
     * present on "Welcome to YOMP" /welcome page.
     */
    static By WELCOME_HELP_TEXT_1 = By
            .xpath(".//*[@id='welcome']/div[2]/div/form/div[1]/p");
    static By WELCOME_HELP_TEXT_2 = By
            .xpath(".//*[@id='welcome']/div[2]/div/form/div[2]/p");
    static By WELCOME_ADVANCE_USER = By.xpath("//div[2][@class='well']/label");
    static By WELCOME_FIRSTTIME_USER = By
            .xpath("//div[1][@class='well']/label");
    static By WELCOME_NEXT_BUTTON = By.xpath("//button[@id='next']");
    static By WELCOME_DEFAULT_SELECTED_RADIOBUTTON = By
            .xpath("//input[@checked]");
    static int WAIT_TIME = 10;

    public static void welcomeTitleVerification(WebDriver driver) {
        String welcomePageTitle = TestUtilities.waitGetText(WELCOME_FORMTITLE,
                driver, WAIT_TIME);
        Assert.assertEquals(welcomePageTitle, "Welcome to YOMP");
    }

    public static void welcomeHelpTextVerification(WebDriver driver) {
        /*
         * Help text present under the "First time user" section on
         * "Welcome to YOMP" page.
         */
        String welcomePageHelpText1 = TestUtilities.waitGetText(
                WELCOME_HELP_TEXT_1, driver, WAIT_TIME);
        /*
         * Help text present under the "Advance User" section on
         * "Welcome to YOMP" page
         */
        String welcomePageHelpText2 = TestUtilities.waitGetText(
                WELCOME_HELP_TEXT_2, driver, WAIT_TIME);
        Assert.assertEquals(welcomePageHelpText1,
                "YOMP will automatically select an initial set of your"
                        + " instances to monitor from this region:");
        Assert.assertEquals(welcomePageHelpText2,
                "Manually select regions and instances.");
    }

    public static void welcomeUserOptionsVerification(WebDriver driver) {
        String welcomeFirstUser = TestUtilities.waitGetText(
                WELCOME_FIRSTTIME_USER, driver, WAIT_TIME);
        String welcomeAdvanceUser = TestUtilities.waitGetText(
                WELCOME_ADVANCE_USER, driver, WAIT_TIME);
        Assert.assertEquals(welcomeFirstUser, "First time user");
        Assert.assertEquals(welcomeAdvanceUser, "Advanced YOMP user");
    }

    public static void welcomeByDefaultRadioButtonSelected(WebDriver driver) {
        Assert.assertTrue(
                driver.findElement(WELCOME_DEFAULT_SELECTED_RADIOBUTTON)
                        .isSelected(),
                "By default first time user is not selected");
    }

    public static void welcomeNextButtonVerification(WebDriver driver) {
        String WelcomeNextButtonLable = TestUtilities.waitGetText(
                WELCOME_NEXT_BUTTON, driver, WAIT_TIME);
        Assert.assertEquals(WelcomeNextButtonLable, "Next");
    }

    public static void welcomeHeader(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testHeaderDuringSetup(driver);
    }

    public static void welcomeFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void welcomeDropdown(WebDriver driver) {
        String welcomedropDown[] = new String[] {
                "ap-northeast-1: Asia Pacific (Tokyo)",
                "ap-southeast-1: Asia Pacific (Singapore)",
                "ap-southeast-2: Asia Pacific (Sydney)",
                "eu-west-1: EU (Ireland)",
                "sa-east-1: South America (Sao Paulo)",
                "us-east-1: US East (Northern Virginia)",
                "us-west-1: US West (Northern California)",
                "us-west-2: US West (Oregon)" };
        int ddlength = welcomedropDown.length;
        List<WebElement> regionName = driver.findElements(By
                .xpath("//select//option"));
        Assert.assertTrue(ddlength == regionName.size());
        for (int locaterIndex = 0; locaterIndex < ddlength; locaterIndex++) {
            String xpathString = String.format("//select//option[%d]",
                    locaterIndex + 1);
            String val = driver.findElement(By.xpath(xpathString)).getText();
            Assert.assertTrue(welcomedropDown[locaterIndex]
                    .equalsIgnoreCase(val));
        }
    }
}
