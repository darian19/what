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

import java.util.HashMap;
import java.util.List;

import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.remote.RemoteWebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

public class TestUtilities {
    static By INSTANCE = By.id(
            "com.YOMPsolutions.YOMP.mobile:id/instance_anomaly_chart");
    static By INSTANCE_METRIC = By.id(
            "com.YOMPsolutions.YOMP.mobile:id/metric_anomaly_chart");
    static By DATE = By.id("com.YOMPsolutions.YOMP.mobile:id/date");
    static By EMAIL_NOTIFICATION = By.name("Notification Email");
    static By EMAIL_TEXT_BOX = By.id("android:id/edit");
    static By OK_BUTTON = By.name("OK");
    static By MOBILE_SETTINGS_BUTTON = By.className(
            "android.widget.ImageButton");
    static By FEEDBACK_BUTTON = By.name("Feedback");
    static By CANCEL_BUTTON = By.id("android:id/button2");
    static By REFRESH_RATE = By.name("Refresh Rate");
    static By RATE_OPTION = By.name("1 minute");
    static By SETTINGS_BUTTON = By.name("Settings");
    static By OK_BUTTON_ON_INVALID_EMAIL = By.id("android:id/button1");
    static By MAX_NOTIFICATION_PER_INSTANCE = By.name(
            "Max Notifications Per Instance");
    static By OPTION_MAX_NOTIFICATION_PER_INSTANCE = By.name("No limit");
    static By TUTORIAL = By.name("Tutorial");
    static By SKIP_TUTORIAL = By.id(
            "com.YOMPsolutions.YOMP.mobile:id/skipTutorialButton");
    static By SCROLL_ELEMENT = By.className("android.widget.ListView");
    static String INVALID_EMAIL_ID = "invalid";
    static String VALID_EMAIL_ID = "test_user@numenta.com";


    public static void swipe(WebDriver driver, boolean forward)
            throws InterruptedException {
        double startXValue, endXValue;
        if (forward) {
            startXValue = 0.95;
            endXValue = 0.05;
        } else {
            startXValue = 0.05;
            endXValue = 0.95;
        }
        JavascriptExecutor js = (JavascriptExecutor) driver;
        HashMap<String, Double> swipeObject = new HashMap<String, Double>();
        swipeObject.put("startX", startXValue);
        swipeObject.put("startY", 0.5);
        swipeObject.put("endX", endXValue);
        swipeObject.put("endY", 0.5);
        swipeObject.put("duration", 1.8);
        js.executeScript("mobile: swipe", swipeObject);
    }


    public static void longPressOnInstance(WebDriver driver)
            throws InterruptedException {
        WebElement clickInstance = driver.findElement(INSTANCE);
        JavascriptExecutor js = (JavascriptExecutor) driver;
        HashMap<String, String> tapObject = new HashMap<String, String>();
        tapObject.put("element", ((RemoteWebElement) clickInstance).getId());
        js.executeScript("mobile: longClick", tapObject);
    }


    public static void waitClick(By locator, WebDriver driver, int value) {
        WebDriverWait wait = new WebDriverWait(driver, value);
        wait.until(ExpectedConditions.presenceOfElementLocated(
                locator)).click();
    }


    public static String waitGetText(By locator, WebDriver driver, int value) {
        WebDriverWait wait = new WebDriverWait(driver, value);
        return wait.until(ExpectedConditions.presenceOfElementLocated(locator))
                .getText();
    }


    public static void checkGraph(String locator, WebDriver driver, int value) {
        By name = By.name(locator);
        waitClick(name, driver, value);
        waitClick(INSTANCE, driver, value);
        waitClick(INSTANCE_METRIC, driver, value);
        waitClick(DATE, driver, value);
    }


    public static void checkTabs(String locator, WebDriver driver, int value) {
        By name = By.name(locator);
        waitClick(name, driver, value);
    }


    public static void sortedBy(By locator, WebDriver driver, int value) {
        waitClick(locator, driver, value);
        waitClick(INSTANCE, driver, value);
        waitClick(INSTANCE_METRIC, driver, value);
        waitClick(DATE, driver, value);
    }

    public static void sortedByTabs(By locator, WebDriver driver, int value) {
        waitClick(locator, driver, value);
    }

    public static void emailNotification(
            String emailid, WebDriver driver, int value) {
        waitClick(EMAIL_NOTIFICATION, driver, value);
        driver.findElement(EMAIL_TEXT_BOX).sendKeys(emailid);
        waitClick(OK_BUTTON, driver, value);
    }


    public static void menuButtonClick(WebDriver driver) {
        HashMap<String, Integer> swipeObject = new HashMap<String, Integer>();
        swipeObject.put("keycode", 82);
        ((JavascriptExecutor)driver).executeScript(
                "mobile: keyevent", swipeObject);
    }


    public static void clickFeedback(WebDriver driver, int value) {
        menuButtonClick(driver);
        waitClick(FEEDBACK_BUTTON, driver, value);
        waitClick(CANCEL_BUTTON, driver, value);
    }


    public static void clickSettingOptionAndChangeSettings( WebDriver driver,
            int value, String deviceName)throws InterruptedException {
        menuButtonClick(driver);
        waitClick(SETTINGS_BUTTON, driver, value);
        waitClick(REFRESH_RATE, driver, value);
        waitClick(RATE_OPTION, driver, value);
        checkBoxes(driver, deviceName);
        // Pass Invalid EmailID
        emailNotification(INVALID_EMAIL_ID, driver, value);
        waitClick(OK_BUTTON_ON_INVALID_EMAIL, driver, value);
        // Pass Valid EmailID
        emailNotification(VALID_EMAIL_ID, driver, value);
        // Clicking on Max Notification Per Instance option
        changeNotificationSettings(driver, value);
    }


    public static void changeNotificationSettings(WebDriver driver, int value) {
        waitClick(MAX_NOTIFICATION_PER_INSTANCE, driver, value);
        waitClick(OPTION_MAX_NOTIFICATION_PER_INSTANCE, driver, value);
        // Clicking on Tutorial option
        waitClick(TUTORIAL, driver,value);
        waitClick(SKIP_TUTORIAL, driver,value);
    }


    public static void checkBoxes(WebDriver driver, String deviceName)
            throws InterruptedException {
        List<WebElement> checkbox =  driver.findElements(
                By.className("android.widget.CheckBox"));
        checkbox.get(1).click();
        checkbox.get(0).click();
        checkbox.get(1).click();
    }
}
