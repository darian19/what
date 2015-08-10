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

package com.YOMP.utils;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.JavascriptExecutor;

public class TestUtilities {
    static By SETUP_PROGRESS_TEXT = By
            .xpath("html/body/div[1]/section/div/div/section/div/div/div[1]");
    static By INSTANCE_COLUMN = By.xpath("//tr/th[1]");
    static By SERVICE_COLUMN = By.xpath("//tr/th[2]");
    static By REGION_COLUMN = By.xpath("//tr/th[3]");
    static By STATUS_COLUMN = By.xpath("//tr/th[4]");
    static By REMOVE_COLUMN = By.xpath("//tr/th[5]");
    static By LOGIN_BUTTON_LOCATOR = By.id("next");
    static By EXPORT_BUTTON = By
            .xpath("//button[@class='export btn btn-default']");
    static By REMOVE_BUTTON = By
            .xpath("//button[@class='delete btn btn-default']");
    static By INSTANCES_CURRENTLY_MONITORED_BY_YOMP_TITLE = By
            .xpath("//div[@id='instance-list']/div/h3");
    static int WAIT_TIME = 10;

    public static void waitClick(By locator, WebDriver driver, int value) {
        WebDriverWait wait = new WebDriverWait(driver, WAIT_TIME);
        wait.until(ExpectedConditions.presenceOfElementLocated(locator));
        JavascriptExecutor executor = (JavascriptExecutor)driver;
        executor.executeScript("arguments[0].click();", driver.findElement(locator));
    }

    public static String waitGetText(By locator, WebDriver driver, int value) {
        WebDriverWait wait = new WebDriverWait(driver, WAIT_TIME);
        return wait.until(ExpectedConditions.presenceOfElementLocated(locator))
                .getText();
    }
}
