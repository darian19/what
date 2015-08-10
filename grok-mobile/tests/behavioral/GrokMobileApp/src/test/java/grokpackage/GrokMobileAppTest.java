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

package YOMPpackage;

import org.testng.AssertJUnit;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import org.testng.annotations.Parameters;

import YOMPpackage.TestUtilities;

import java.net.URL;
import java.util.List;

import org.junit.Assert;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.rules.TestRule;
import org.junit.rules.Timeout;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.remote.DesiredCapabilities;
import org.openqa.selenium.remote.RemoteWebDriver;

public class YOMPMobileAppTest {
    private WebDriver driver;
    static int WAIT_TIME = 10000;
    static By SIGN_IN = By.name("Sign in");
    static By ANOMALIES = By
            .id("com.YOMPsolutions.YOMP.mobile:id/sortByAnomalies");
    static By NAME = By.id("com.YOMPsolutions.YOMP.mobile:id/sortByName");
    static By HOUR = By.name("HOUR");
    static By DAY = By.name("DAY");
    static By WEEK = By.name("WEEK");
    static By EXIT_TUTORIAL = By
            .id("com.YOMPsolutions.YOMP.mobile:id/skipTutorialButton");
    static By SKIP_TUTORIAL = By
            .id("com.YOMPsolutions.YOMP.mobile:id/skipTutorialButton");
    static By INSTANCE = By
            .id("com.YOMPsolutions.YOMP.mobile:id/instance_anomaly_chart");
    static By NOTIFICATION = By
            .id("com.YOMPsolutions.YOMP.mobile:id/menu_notifications");
    static By CLOSE_BUTTON = By
            .id("com.YOMPsolutions.YOMP.mobile:id/action_close_notifications");
    static By DATE = By.id("com.YOMPsolutions.YOMP.mobile:id/date");
    static By LABEL_ACTIVITY_LOG = By.id("android:id/title");
    static By LABEL_CONNECT_SERVER = By.name("Connect to your server");
    static By LABEL_SETUP = By.id("android:id/action_bar_title");
    static By LABEL_SORTEDBY = By
            .id("com.YOMPsolutions.YOMP.mobile:id/sortTitleText");
    static By ADD_ANOTATION_POP_UP = By.name("Add Annotation");
    static By ANOTATION_NAME = By
    		.id("com.YOMPsolutions.YOMP.mobile:id/txt_name");
    static By ANOTATION_DESCRIPTION = By
            .id("com.YOMPsolutions.YOMP.mobile:id/txt_annotation_message");
    static By ANOTATION_SAVE_BUTTON = By
            .id("com.YOMPsolutions.YOMP.mobile:id/btn_save_annotation");
    static By ANOTATION_DELETE_BUTTON = By
            .id("com.YOMPsolutions.YOMP.mobile:id/btn_annotation_delete");
    static By SHARE_BUTTON = By.name("Share");
    static By OK_BUTTON = By.name("OK");

    @BeforeClass
    @Parameters({ "deviceName", "version", "sauceUserName", "sauceAccessKey" })
    public void setUp(String deviceName, String platformVersion,
            String sauceUserName, String sauceAccessKey) throws Exception {
        DesiredCapabilities capabilities = new DesiredCapabilities();
        capabilities.setCapability("name", "YOMP mobile Testing");
        capabilities.setCapability("app",
                "sauce-storage:YOMP-mobile-app-release.apk");
        capabilities.setCapability("platformName", "Android");
        capabilities.setCapability("device-orientation", "portrait");
        capabilities.setCapability("deviceName", deviceName);
        capabilities.setCapability("platformVersion", platformVersion);
        capabilities.setCapability("androidPackage",
                "com.YOMPsolutions.YOMP.mobile");
        capabilities.setCapability("appActivity",
                "com.YOMPsolutions.YOMP.mobile.SplashScreenActivity");
        driver = new RemoteWebDriver(new URL("http://" + sauceUserName + ":"
                + sauceAccessKey + "@ondemand.saucelabs.com:80/wd/hub"),
                capabilities);
        Thread.sleep(1000);
    }


    @Rule public TestRule timeout1 = new Timeout(30000);
    @Test(priority = 0)
    @Parameters({ "url", "pwd" })
    public void login(String serverUrl, String password)
            throws InterruptedException {
        List<WebElement> allText = driver.findElements(By
                .className("android.widget.EditText"));
        String connectServer = TestUtilities.waitGetText(LABEL_CONNECT_SERVER,
                driver, WAIT_TIME);
        AssertJUnit.assertEquals(connectServer, "Connect to your server");
        String setUp = TestUtilities
                .waitGetText(LABEL_SETUP, driver, WAIT_TIME);
        AssertJUnit.assertEquals(setUp, "Setup");
        // Sign IN
        allText.get(0).sendKeys(serverUrl);
        allText.get(1).sendKeys(password);
        TestUtilities.waitClick(SIGN_IN, driver, WAIT_TIME);
    }


    @Rule public TestRule timeout2 = new Timeout(30000);
    @Test(priority = 1, dependsOnMethods = { "login" })
    public void skipTutorial() throws InterruptedException {
        // SKIP TUTORIAL
        String skipTutorial = TestUtilities.waitGetText(SKIP_TUTORIAL, driver,
                WAIT_TIME);
        AssertJUnit.assertEquals(skipTutorial, "Skip Tutorial");
        // Swipe
        TestUtilities.swipe(driver, true);
        TestUtilities.swipe(driver, true);
        TestUtilities.swipe(driver, true);
        // Exit Tutorial
        TestUtilities.waitClick(EXIT_TUTORIAL, driver, WAIT_TIME);
    }


    @Rule public TestRule timeout3 = new Timeout(30000);
    @Test(priority = 2, dependsOnMethods = { "skipTutorial" })
    public void mainPage() throws InterruptedException {
        String sortedBy = TestUtilities.waitGetText(LABEL_SORTEDBY, driver,
                WAIT_TIME);
        AssertJUnit.assertEquals(sortedBy, "sorted by");
        TestUtilities.waitClick(NOTIFICATION, driver, WAIT_TIME);
        String ActivityLog = TestUtilities.waitGetText(LABEL_ACTIVITY_LOG,
                driver, WAIT_TIME);
        Assert.assertEquals(ActivityLog, "Activity Log");
        TestUtilities.waitClick(CLOSE_BUTTON, driver, WAIT_TIME);
    }


    @Rule public TestRule timeout4 = new Timeout(30000);
    @Test(priority = 3, dependsOnMethods = { "mainPage" })
    public void pageModules() throws InterruptedException {
        String[] tabName = { "DAY", "WEEK", "HOUR" };
        for (int i = 0; i < tabName.length; i++) {
            TestUtilities.checkTabs(tabName[i], driver, WAIT_TIME);
        }
        TestUtilities.sortedByTabs(NAME, driver, WAIT_TIME);
        TestUtilities.sortedByTabs(ANOMALIES, driver, WAIT_TIME);
    }


    @Rule public TestRule timeout5 = new Timeout(30000);
    @Test(priority = 4, dependsOnMethods = { "pageModules" })
    public void swipeRightAndLeft() throws InterruptedException {
        TestUtilities.swipe(driver, true);
        TestUtilities.swipe(driver, false);
    }


    @Rule public TestRule timeout6 = new Timeout(30000);
    @Test(priority = 5, dependsOnMethods = { "swipeRightAndLeft" })
    @Parameters({ "deviceName" })
    public void settings(String deviceName) throws InterruptedException {
        if (deviceName.isEmpty()) {
            return;
        }
        if (deviceName.contains("Nexus")) {
            // Clicking on Feedback option
            TestUtilities.clickFeedback(driver, WAIT_TIME);
            // Clicking on Settings option
            TestUtilities.clickSettingOptionAndChangeSettings(driver,
                    WAIT_TIME, deviceName);
        } else {
            System.out
                    .println("Non-Nexus test device with a hardware Settings button"
                            + " hence Settings page cannot be tested correctly.");
        }
        driver.navigate().back();
    }


    @Ignore("TAUR-1120: Failing because 'add-annotation-pop-up' crashes")
    public void addAnnotation() throws InterruptedException {
        TestUtilities.longPressOnInstance(driver);
        TestUtilities.waitClick(ADD_ANOTATION_POP_UP, driver, WAIT_TIME);
        String annotation = TestUtilities.waitGetText(ADD_ANOTATION_POP_UP,
                driver, WAIT_TIME);
        AssertJUnit.assertEquals(annotation, "Add Annotation");
        driver.findElement(ANOTATION_NAME).sendKeys("Invalid");
        driver.findElement(ANOTATION_DESCRIPTION).sendKeys("Anomoly detected");
        TestUtilities.waitClick(DATE, driver, WAIT_TIME);
    }


    @AfterClass
    public void tearDown() throws Exception {
        driver.quit();
    }
}
