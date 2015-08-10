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

public class InstallYOMPMobileAppTest {
    static By SETUP_COMPLETE_TITLE = By
            .xpath("//section[@id='content']/div/div/h1");
    static By SETUP_COMPLETE_HELP_TEXT = By
            .xpath("html/body/div[1]/section/div/div/p[1]");
    static By SETUP_COMPLETE_REQUIREMENT = By
            .xpath("//div[@class='well']/strong");
    static By SETUP_COMPLETE_REQUIREMENT_HELP_TEXT_1 = By
            .xpath("//div[@class='well']/ul/li[1]");
    /*
     * Each of SETUP_COMPLETE_STEP_# / is one of the steps under "Requirements"
     * section in the /complete page.
     */
    static By SETUP_COMPLETE_STEP_1 = By.xpath("//ol[@class='steps']/li[1]");
    static By SETUP_COMPLETE_STEP_2 = By
            .xpath("//ol[@class='steps']/li[2]/ol/li[2]");
    static By SETUP_COMPLETE_STEP_3 = By
            .xpath("//ol[@class='steps']/li[3]/strong");
    static By SETUP_COMPLETE_SERVER_URL = By.xpath("//dl/dt[1]");
    static By SETUP_COMPLETE_PASSWORD = By.xpath("//dl/dt[2]");
    static By SETUP_COMPLETE_ANDRIOD_LOGO = By
            .xpath("//img[@src='/static/img/mobile/play-store-button.png']");
    static By SETUP_COMPLETE_REQUIREMENT_SECTION_URL = By
            .xpath("//div[@class='well']/ul/li[2]/a");
    static By SETUP_SERVER_URL = By.xpath("//dl/dd[1]/code");
    static By SETUP_COMPLETE_MANAGE_MONITORED_INSTANCES = By
            .xpath("//button[@id='next']");
    static By SETUP_COMPLETE_PROGRESS_BAR = By.id("progress-bar-container");
    static By SETUP_COMPLETE_STEP_PROGRESS = By
            .xpath("//div[@class='text-muted']/span");
    static int WAIT_TIME = 10;

    public static void installYOMPMobileAppTitleVerification(WebDriver driver) {
        String installYOMPMobileAppPageHelpText = TestUtilities.waitGetText(
                SETUP_COMPLETE_HELP_TEXT, driver, WAIT_TIME);
        String installYOMPMobileAppPageTitle = TestUtilities.waitGetText(
              SETUP_COMPLETE_TITLE, driver, WAIT_TIME);
        boolean checkContains1 = installYOMPMobileAppPageTitle.contains("Install YOMP Mobile App");
        Assert.assertEquals(checkContains1,true,"PAGE TITLE IS WRONG");
        Assert.assertEquals(installYOMPMobileAppPageHelpText,
                "Your server set up is now complete. "
        + "You need to install the Mobile App to begin using YOMP.");
    }

    public static void installYOMPMobileAppRequirementSection(WebDriver driver) {
        String installYOMPMobileAppPageRequirementTitle = TestUtilities
                .waitGetText(SETUP_COMPLETE_REQUIREMENT, driver, WAIT_TIME);
        String installYOMPMobileAppPageCompleteRequirementHelpText =
        TestUtilities.waitGetText(SETUP_COMPLETE_REQUIREMENT_HELP_TEXT_1,
            driver, WAIT_TIME);
        Assert.assertEquals(installYOMPMobileAppPageRequirementTitle,
                "Requirements:");
        Assert.assertEquals(
                installYOMPMobileAppPageCompleteRequirementHelpText,
                "Ensure that you are running Android 4.0.3 or later.");
    }

    public static void installYOMPMobileAppStepsVerification(WebDriver driver)
            throws InterruptedException {
        /*
         * 1st step under "Requirements" section i.e.
         * "Install the YOMP app via the Play Store by clicking"
         */
        String installYOMPMobileAppsteps1 = TestUtilities.waitGetText(
                SETUP_COMPLETE_STEP_1, driver, WAIT_TIME);
        String installYOMPMobileAppServerUrlLabel = TestUtilities.waitGetText(
                SETUP_COMPLETE_SERVER_URL, driver, WAIT_TIME);
        String installYOMPMobileAppPasswordLabel = TestUtilities.waitGetText(
                SETUP_COMPLETE_PASSWORD, driver, WAIT_TIME);
        /* 2nd step under "Requirements" section i.e. Tap the Sign In button. */
        String installYOMPMobileAppsteps2 = TestUtilities.waitGetText(
                SETUP_COMPLETE_STEP_2, driver, WAIT_TIME);
        /* 3rd step under"Requirements" section i.e. Finished! */
        String installYOMPMobileAppsteps3 = TestUtilities.waitGetText(
                SETUP_COMPLETE_STEP_3, driver, WAIT_TIME);
        Assert.assertTrue(driver.findElement(SETUP_COMPLETE_ANDRIOD_LOGO)
                .isDisplayed(), "Logo is not present");
        Assert.assertEquals(installYOMPMobileAppsteps1,
                "Install the YOMP app via the Play Store by clicking:");
        Assert.assertEquals(installYOMPMobileAppServerUrlLabel, "Server URL");
        Assert.assertEquals(installYOMPMobileAppPasswordLabel,
                "Password (case sensitive)");
        Assert.assertEquals(installYOMPMobileAppsteps2,
                "Tap the Sign In button.");
        Assert.assertEquals(installYOMPMobileAppsteps3, "Finished!");
    }

    /*
     * This test asserts whether the URL in the "Requirements" section is same
     * as that of url under the section "Server URL".
     */
    public static void installYOMPMobileAppCompareRequirementSectionAndSetupServerURL(
            WebDriver driver) {
        String requirementsSectionUrl = TestUtilities.waitGetText(
                SETUP_COMPLETE_REQUIREMENT_SECTION_URL, driver, WAIT_TIME);
        String serverUrl = TestUtilities.waitGetText(SETUP_SERVER_URL, driver,
                WAIT_TIME);
        Assert.assertTrue(requirementsSectionUrl.contains(serverUrl),
                "Requirements Section URL is not same as that of Server URL.");
    }

    public static void installYOMPMobileAppSetUpProgressBarVerification(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testSetUpProgressText(driver);
    }

    public static void installYOMPAppFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void installYOMPAppHeader(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testHeaderDuringSetup(driver);
    }

    public static void installYOMPMobileAppManageMonitoredInstancesButton(
            WebDriver driver) throws InterruptedException {
        String completeManagebutton = TestUtilities.waitGetText(
                SETUP_COMPLETE_MANAGE_MONITORED_INSTANCES, driver, WAIT_TIME);
        TestUtilities.waitClick(SETUP_COMPLETE_MANAGE_MONITORED_INSTANCES,
                driver, WAIT_TIME);
        Assert.assertEquals(completeManagebutton, "Manage Monitored Instances");
    }
}
