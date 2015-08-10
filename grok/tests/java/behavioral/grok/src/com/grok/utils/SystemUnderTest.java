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

import java.net.MalformedURLException;
import java.net.URL;

import java.util.concurrent.TimeUnit;

import org.openqa.selenium.remote.DesiredCapabilities;
import org.openqa.selenium.remote.RemoteWebDriver;
import org.openqa.selenium.WebDriver;

public class SystemUnderTest {
    private static WebDriver driver;
    static String SAUCEURL = "@ondemand.saucelabs.com:80/wd/hub";

    public static WebDriver getDriverInstance() {
        if (driver == null)
            System.exit(0);
        return driver;
    }

    public static void load(String url, String os, String browser,
            String saucename, String saucekey) throws MalformedURLException {
        DesiredCapabilities capabilities = new DesiredCapabilities();
        capabilities.setCapability("platform", os);
        capabilities.setBrowserName(browser);
        capabilities.setCapability("name", "YOMP Sauce Testing");
        System.out.println(saucekey);
        System.out.println(saucename);
        driver = new RemoteWebDriver(new URL("http://" + saucename + ":"
                + saucekey + SAUCEURL), capabilities);
        driver.manage().window().maximize();
        driver.manage().timeouts().implicitlyWait(40000, TimeUnit.SECONDS);
        driver.get(url);
    }
}
