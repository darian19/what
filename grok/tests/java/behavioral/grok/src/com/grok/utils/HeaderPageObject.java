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

public class HeaderPageObject {
    private WebDriver driver;

    static By YOMP_LOGO = By.xpath("//a[@class='navbar-brand']");
    static By HELP_LOGO = By.xpath("//li[@class='help']");
    static By MANAGE_TAB = By.xpath("//li/a[@href='/YOMP']");
    static By CHARTS = By.xpath("//li/a[@href='/YOMP/embed/charts']");
    static By SETUP_DROPDOWN = By.xpath("//li/a[@href='/YOMP/welcome']");

    public HeaderPageObject(WebDriver driver) {
        this.driver = driver;
    }

    public String YOMPLogo() {
        return driver.findElement(YOMP_LOGO).getText();

    }

    public String helpLogo() {
        return driver.findElement(HELP_LOGO).getText();
    }

    public boolean chartsTab() {
        return driver.findElement(CHARTS).isDisplayed();
    }

    public boolean manageTab() {
        return driver.findElement(MANAGE_TAB).isDisplayed();
    }

    public boolean setupDropDown() {
        return driver.findElement(SETUP_DROPDOWN).isDisplayed();
    }
}
