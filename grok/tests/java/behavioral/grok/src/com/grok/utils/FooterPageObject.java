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

public class FooterPageObject {
    private WebDriver driver;

    static By ABOUT_LINK = By.linkText("About");
    static By HELP_LINK = By.linkText("Help");
    static By NUMENTA_LINK = By.linkText("Numenta");

    public FooterPageObject(WebDriver driver) {
        this.driver = driver;
    }

    public String aboutLink() {
        return driver.findElement(ABOUT_LINK).getText();
    }

    public String helpLink() {
        return driver.findElement(HELP_LINK).getText();
    }

    public String numentaLink() {
        return driver.findElement(NUMENTA_LINK).getText();
    }
}
