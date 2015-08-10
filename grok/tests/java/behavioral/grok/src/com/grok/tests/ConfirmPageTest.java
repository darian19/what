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

public class ConfirmPageTest {

    static By CONFIRM_FORM_TITLE = By.xpath("//section[@id='content']/div/div/h1");
    static By CONFIRM_HELP_TEXT_1 = By.xpath(".//*[@id='content']/div/div/ul/li[1]");
    static By CONFIRM_HELP_TEXT_2 = By.xpath(".//*[@id='content']/div/div/ul/li[2]");
    static By CONFIRM_HELP_TEXT_3 = By.xpath(".//*[@id='content']/div/div/ul/li[3]");
    static By CONFIRM_BUTTON_BACK = By.xpath("//button[@id='back']");
    static By CONFIRM_BUTTON_NEXT = By.xpath("//button[@id='next']");
    static By CONFIRM_SETUP_PROGRESS = By.xpath("//div[@class='text-muted']/span");
    static By CONFIRM_LABEL_AUTOSCALING_GROUP = By.xpath("//form[@id='confirmed-instances']/fieldset/div/h3[1]");
    static By CONFIRM_LABEL_EC2INSTANCES = By.xpath("//form[@id='confirmed-instances']/fieldset/div/h3[2]");
    static By CONFIRM_LABEL_ELBINSTANCES = By.xpath("//form[@id='confirmed-instances']/fieldset/div/h3[3]");
    static By CONFIRM_LABEL_RDSINSTANCES = By.xpath("//form[@id='confirmed-instances']/fieldset/div/h3[4]");
    static int WAIT_TIME = 10;

    public static void confirmTitleVerification(WebDriver driver) {
        String confirmPageTitle = TestUtilities.waitGetText(CONFIRM_FORM_TITLE,
                driver, WAIT_TIME);
        System.out.println(confirmPageTitle);
        Assert.assertEquals(confirmPageTitle, "Step 3: Select Instances to Monitor");
    }

    public static void confirmPageLabelVerification(WebDriver driver) {
        String confirmAutoscalingLabel = TestUtilities.waitGetText(
                CONFIRM_LABEL_AUTOSCALING_GROUP, driver, WAIT_TIME);
        String confirmEC2Label = TestUtilities.waitGetText(
                CONFIRM_LABEL_EC2INSTANCES, driver, WAIT_TIME);
        String confirmELBLabel = TestUtilities.waitGetText(
                CONFIRM_LABEL_ELBINSTANCES, driver, WAIT_TIME);
        String confirmRDSLabel = TestUtilities.waitGetText(
                CONFIRM_LABEL_RDSINSTANCES, driver, WAIT_TIME);
        Assert.assertEquals(confirmAutoscalingLabel, "Autoscaling Groups");
        Assert.assertEquals(confirmEC2Label, "EC2 Instances");
        Assert.assertEquals(confirmELBLabel, "ELB Instances");
        Assert.assertEquals(confirmRDSLabel, "RDS Instances");
    }

    public static void confirmPageHelpTextVerification(WebDriver driver) throws InterruptedException {
        String confirmPageHelpText1 = TestUtilities.waitGetText(
                CONFIRM_HELP_TEXT_1, driver, WAIT_TIME);
        String confirmPageHelpText2 = TestUtilities.waitGetText(
                CONFIRM_HELP_TEXT_2, driver, WAIT_TIME);
        String confirmPageHelpText3 = TestUtilities.waitGetText(
                CONFIRM_HELP_TEXT_3, driver, WAIT_TIME);
        Assert.assertEquals(confirmPageHelpText1, "To get you started quickly, YOMP has "
                + "automatically selected some of the largest and longest "
                + "running instances from your AWS environment and "
                + "suggested 8 of these for YOMP to monitor.");
        Assert.assertEquals(confirmPageHelpText2, "You can change - or simply confirm these selections.");
        Assert.assertEquals(confirmPageHelpText3, "You can also change these selections after installation,"
                + " including adding additional instances or regions to support monitoring of "
                + "your entire AWS environment.");
    }
    public static void confirmPageButtonVerification(WebDriver driver) {
        String confirmNextButton = TestUtilities.waitGetText(CONFIRM_BUTTON_NEXT,
                driver, WAIT_TIME);
        String confirmBackButton = TestUtilities.waitGetText(CONFIRM_BUTTON_BACK,
                driver, WAIT_TIME);
        Assert.assertEquals(confirmNextButton, "Next");
        Assert.assertEquals(confirmBackButton, "Back");
    }

    public static void confirmPageHeader(WebDriver driver) throws InterruptedException {
        ReusableTests.testHeaderDuringSetup(driver);
    }

    public static void confirmPageFooter(WebDriver driver) throws Exception {
        ReusableTests.testFooter(driver);
    }

    public static void confirmPageSetUpProgressBarVerification(WebDriver driver)
            throws InterruptedException {
        ReusableTests.testSetUpProgressText(driver);
    }

    public static void confirmPageNextButtonClick(WebDriver driver) {
        TestUtilities.waitClick(CONFIRM_BUTTON_NEXT, driver, WAIT_TIME);
    }
}
