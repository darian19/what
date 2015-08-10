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

import com.YOMP.utils.SystemUnderTest;
import com.YOMP.utils.TestUtilities;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.Properties;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Parameters;
import org.testng.annotations.Test;

public class AdvancedUserYOMP {
    private WebDriver driver;
    Properties props = new Properties();
    static By FIRST_TIME_USER = By.xpath(".//*[@id='novice']");
    static By ADV_USER = By.xpath("//input[@id='expert']");
    static By NEXT_BUTTON = By.xpath("//button[@id='next']");
    static String FIRST_TIME = "FIRST_TIME";
    static int WAIT_TIME = 10;

    @BeforeClass
    @Parameters({ "serverURL", "os", "browser", "saucename", "saucekey" })
    public void setUp(String serverURL, String os, String browser,
            String saucekey, String saucename) throws FileNotFoundException,
            IOException {
        System.out.println(serverURL);
        SystemUnderTest.load(serverURL, os, browser, saucekey, saucename);
        driver = SystemUnderTest.getDriverInstance();
    }

    @Test(priority = 0)
    @Parameters("usertype")
    public void welcomePageValidation(String usertype) throws Exception {
        WelcomeTest.welcomeTitleVerification(driver);
        WelcomeTest.welcomeByDefaultRadioButtonSelected(driver);
        WelcomeTest.welcomeHelpTextVerification(driver);
        WelcomeTest.welcomeHeader(driver);
        WelcomeTest.welcomeFooter(driver);
        WelcomeTest.welcomeUserOptionsVerification(driver);
        WelcomeTest.welcomeDropdown(driver);
        if (FIRST_TIME.equals(usertype)) {
            TestUtilities.waitClick(FIRST_TIME_USER, driver, WAIT_TIME);
            TestUtilities.waitClick(NEXT_BUTTON, driver, WAIT_TIME);
        } else {
            TestUtilities.waitClick(ADV_USER, driver, WAIT_TIME);
            TestUtilities.waitClick(NEXT_BUTTON, driver, WAIT_TIME);
        }
    }

    @Test(priority = 1)
    public void registationPageValidation() throws Exception {
        RegistrationTest.registrationTitleVerification(driver);
        RegistrationTest.registrationsHeader(driver);
        RegistrationTest.registrationsFooter(driver);
        RegistrationTest.registrationHeadingHelpTextVerification(driver);
        RegistrationTest.registrationLabelVerification(driver);
        RegistrationTest.registrationButtonVerification(driver);
        RegistrationTest.registrationSetUpProgressBarVerification(driver);
        RegistrationTest.registrationCheckboxVerification(driver);
        RegistrationTest.registrationInvalidEmailIdVerification(driver);
        RegistrationTest
                .registrationDisabledNextButtonUsingBothCheckBoxes(driver);
        RegistrationTest.registrationDisabledNextButtonUsingCheckbox1(driver);
        RegistrationTest.registrationEnabledNextButtonUsingCheckbox2(driver);
        RegistrationTest
                .registrationEnabledNextButtonUsingBothCheckboxes(driver);
        RegistrationTest.registrationNextButtonClick(driver);
    }

    @Test(priority = 2)
    @Parameters({ "accessKeyID", "secretKey" })
    public void authPageVerification(String accessKeyID, String secretKey)
            throws Exception {
        AuthTest.authHelpTextVerification(driver);
        AuthTest.authTitleVerification(driver);
        AuthTest.authSetUpProgressBarVerification(driver);
        AuthTest.authButtonVerification(driver);
        AuthTest.authHeader(driver);
        AuthTest.authFooter(driver);
        AuthTest.authTitleVerification(driver);
        AuthTest.authLabelVerification(driver);
        AuthTest.authInvalidCredentialIdVerification(driver);
        AuthTest.authValidAccessKeyIDInvalidSecretKeyVerification(accessKeyID,
                driver);
        AuthTest.authInvalidAccessKeyIDValidSecretKeyVerification(secretKey,
                driver);
        AuthTest.typeAccessKeyID(accessKeyID, driver);
        AuthTest.typeSecretKey(secretKey, driver);
        AuthTest.submitLogin(driver);
    }

    @Test(priority = 3)
    @Parameters("usertype")
    public void confirmPageValidation(String usertype)
            throws Exception {
        if (FIRST_TIME.equals(usertype)) {
            ConfirmPageTest.confirmPageLabelVerification(driver);
            ConfirmPageTest.confirmPageHelpTextVerification(driver);
            ConfirmPageTest.confirmPageButtonVerification(driver);
            ConfirmPageTest.confirmPageHeader(driver);
            ConfirmPageTest.confirmPageFooter(driver);
            ConfirmPageTest.confirmPageSetUpProgressBarVerification(driver);
            ConfirmPageTest.confirmPageNextButtonClick(driver);
        } else {
            System.out.println("Using Advanced User, hence skipping `Confirm Page` tests.");
        }
    }

    @Test(priority = 4)
    public void installMobileAppPageValidation() throws Exception {
        InstallYOMPMobileAppTest.installYOMPMobileAppTitleVerification(driver);
        InstallYOMPMobileAppTest.installYOMPMobileAppRequirementSection(driver);
        InstallYOMPMobileAppTest.installYOMPMobileAppStepsVerification(driver);
        InstallYOMPMobileAppTest
                .installYOMPMobileAppCompareRequirementSectionAndSetupServerURL(driver);
        InstallYOMPMobileAppTest.installYOMPAppFooter(driver);
        InstallYOMPMobileAppTest.installYOMPAppHeader(driver);
        InstallYOMPMobileAppTest.installYOMPMobileAppSetUpProgressBarVerification(driver);
        InstallYOMPMobileAppTest
                .installYOMPMobileAppManageMonitoredInstancesButton(driver);
    }

    @Test(priority = 5)
    public void managePageValidation() throws Exception {
        ManageTest.manageTitleVerification(driver);
        ChartTest.goToChartPageAndCheckMessage(driver);
        ManageTest.manageExportRemoveCheckAfterAddingInstances(driver);
        ManageTest.allowTechSupportAccess(driver);
        ManageTest.revokeTechSupportAccess(driver);
        ManageTest
                .manageInstancesCurrentlyMonitoredByYOMPSectionVerification(driver);
        ManageTest.monitorAdditionalInstancesDropDownVerification(driver);
        ManageTest.addYOMPToWebPageTitleVerification(driver);
        ManageTest.YOMPToWebPageHelpTextVerification(driver);
        ManageTest.manageTextBoxesVerification(driver);
        ManageTest.manageHeader(driver);
        ManageTest.manageFooter(driver);
        ManageTest.testDropDown(driver);
        ManageTest.navigateSBNTPage(driver);
    }

    @Test(priority = 6)
    public void searchByNameTagPageValidation() throws Exception {
        SearchByNameTagPage.pageTitleVerification(driver);
        SearchByNameTagPage.cancelRemoveInstances(driver);
        SearchByNameTagPage.removeInstances(driver);
        SearchByNameTagPage.headingHelpTextVerification(driver);
        SearchByNameTagPage.labelVerification(driver);
        SearchByNameTagPage.header(driver);
        SearchByNameTagPage.footer(driver);
        SearchByNameTagPage.errorSelectingRegion(driver);
        SearchByNameTagPage.selectInstanceWithRegionWithoutTagName(driver);
        SearchByNameTagPage.selectingInstances(driver);
        SearchByNameTagPage.exportAndRemoveButtonsVerification(driver);
        SearchByNameTagPage.pageSectionTitleVerification(driver);
        SearchByNameTagPage.columnVerification(driver);
        SearchByNameTagPage.removeInstanceByClickingCrossButton(driver);
        SearchByNameTagPage.navigateAutoStack(driver);
    }

    @Test(priority = 7)
    public void autoStackPageValidation() throws Exception {
        AutoStackPage.autoStackPageHelpTextVerification(driver);
        AutoStackPage.autoStackPageTitleVerification(driver);
        AutoStackPage.autoStackPageFormVerification(driver);
        AutoStackPage.autoStackPageFormLabelVerification(driver);
        AutoStackPage.autoStackPageFormHelpTextVerification(driver);
        AutoStackPage.autoStackCreationVerification(driver);
        AutoStackPage.autoStackPageTextBoxesVerification(driver);
        AutoStackPage.autoStackPageButtonVerification(driver);
        AutoStackPage.autoStackPageHeader(driver);
        AutoStackPage.autoStackPageFooter(driver);
        AutoStackPage.autoStackPageDoneButtonVerification(driver);
        AutoStackPage.navigateBrowsePage(driver);
    }

    @Test(priority = 8)
    public void browsePageValidation() throws Exception {
        BrowseTest.browsePageTitleVerification(driver);
        BrowseTest.browsePageHelpTextVerification(driver);
        BrowseTest.browsePageSelectInstance(driver);
        BrowseTest.browseClickOnInstance(driver);
        BrowseTest.browsePageSectionTitleVerification(driver);
        BrowseTest.browseColumnVerification(driver);
        BrowseTest.browseHeader(driver);
        BrowseTest.browseFooter(driver);
        BrowseTest.browseExportAndRemoveButtonsVerification(driver);
        BrowseTest.navigateNotificationPage(driver);
    }

    @Test(priority = 9)
    public void notificationPageValidation() throws Exception {
        NotificationPage.notificationPageTitleVerification(driver);
        NotificationPage.notificationPageHelpTextVerification(driver);
        NotificationPage.notificationPageLabelVerification(driver);
        NotificationPage.notificationPageButtonVerification(driver);
        NotificationPage.notificationPageHeader(driver);
        NotificationPage.notificationPageFooter(driver);
        NotificationPage.navigateCustomMetric(driver);
    }

    @Test(priority = 10)
    public void customMetricPageValidation() throws Exception {
        CustomMetricTest.customMetricPageTitleVerification(driver);
        CustomMetricTest.customMetricHeader(driver);
        CustomMetricTest.customMetricFooter(driver);
        CustomMetricTest.customMetricDoneButtonVerification(driver);
        CustomMetricTest.navigateImport(driver);
    }

    @Test(priority = 11)
    public void importPageValidation() throws Exception {
        ImportTest.importTitleVerification(driver);
        ImportTest.importHelpTextVerification(driver);
        ImportTest.importColumnVerification(driver);
        ImportTest.importHeader(driver);
        ImportTest.importFooter(driver);
        ImportTest.importExportRemoveButtonVerification(driver);
        ImportTest.importSectionTitleVerification(driver);
        ImportTest.importDoneButtonVerification(driver);
    }

    @AfterClass
    public void tearDown() throws InterruptedException {
        driver.quit();
    }
}
