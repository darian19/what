/* ----------------------------------------------------------------------
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
 * ---------------------------------------------------------------------- */

(function($) {

    var windowOnscroll; // used for global throbber

    if (! window.YOMPUI.utils) {
        window.YOMPUI.utils = {};
    }

    /**
     * sync logScale function with mobile app
     */
    YOMPUI.utils.logScale = function(value) {
        if(value > 0.99999) {
            return 1;
        }
        return (
            Math.log(1.0000000001 - value) /
            Math.log(1.0 - 0.9999999999)
        );
    };

    /**
     * Encode/Escape XML Entities [<>'"&] within a string. Used to prep JSON
     *  for storage in inline html data-attributes.
     * @param {string} str Input string to encode and escape any XML ents for.
     * @returns {string} Encoded string.
     */
    YOMPUI.utils.encodeXmlEntities = function(str) {
        return str.replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&apos;');
    };

    /**
     * Grab a URL parameter, i.e. "?name=Person"
     * @param {string} key URL Param key value ("name")
     * @returns {string} URL Param value for specific key ("Person")
     */
    YOMPUI.utils.getUrlParam = function(key) {
        var params = window.location.search.replace(/^\?/,'').split('&'),
            value,
            find = function(param) {
                var parts = param.split('='),
                    keyPart = parts[0],
                    valPart = parts[1];

                if(key === keyPart) {
                    value = valPart;
                    return true;
                }
            },
            found = params.some(find);

        return value;
    };

    /**
     * Is the user "Logged In" and authorized?
     * @returns {boolean} Does localStorage contain apiKey value?
     */
    YOMPUI.utils.isAuthorized = function() {
        return YOMPUI.utils.store.get('apiKey') ? true : false;
    };

    /**
     * Is URL for any Setup Flow?
     * @returns {boolean} Does URL contain 'setup' flow flag?
     */
    YOMPUI.utils.isSetupFlow = function() {
        return YOMPUI.utils.getUrlParam('setup') ? true : false;
    };

    /**
     * Is URL for Expert Setup Flow?
     * @returns {boolean} Does URL contain 'expert' setup flow flag?
     */
    YOMPUI.utils.isExpert = function() {
        return YOMPUI.utils.getUrlParam('expert') ? true : false;
    };

    /**
     * How many steps in basic setup vs. expert setup?
     */
    YOMPUI.utils.getSetupTotalSteps = function() {
        var type = YOMPUI.utils.isExpert() ? "expert" : "normal";
        return YOMPUI.msgs('site').setup.steps[type];
    };

    /**
     * Get Backbone.View for setup progress bar
     */
    YOMPUI.utils.getSetupProgressBar = function(step, el) {
        var total = YOMPUI.utils.getSetupTotalSteps(),
            percent = Math.floor(100 * (step - 1) / (total - 1));

        return new YOMPUI.SetupProgressBarView({
            el:      el,
            current: step,
            total:   total,
            percent: percent
        }).render();
    };

    /**
     * Global basic user error UI interaction
     */
    YOMPUI.utils.modalError = function(error) {
        var regex = {
                apiKey: /Invalid API Key/,
                awsSecret: /request signature we calculated/,
                quota: /Server limit exceeded;.*limit=(\d+)\./
            },
            limit,
            title = 'Error',
            body = "Sorry! A problem was encountered. Please try again.",
            message = error || 'An unknown error occured.';

        YOMPUI.utils.throb.stop();

        if(message.match(regex.apiKey)) {
            YOMPUI.utils.store.clear('apiKey');
            YOMPUI.utils.go('/YOMP/welcome');
            return;
        }
        if(message.match(regex.awsSecret)) {
            message = 'AWS was not able to validate the provided secret access credential.';
        }
        if(message.match(regex.quota)) {
            limit = message.match(regex.quota)[1];
            edition = YOMPUI.product.edition;
            title = 'Limit Reached';
            body = 'Sorry, YOMP is limited to monitoring ' + limit + ' instances and AutoStacks on an AWS EC2 server of the current size.';
            message = 'Please upgrade to a bigger AWS EC2 instance type in order to <a href="http://www.numenta.com/assets/pdf/YOMP/resources/1.5/Upgrade-AWS-EC2-Instance-Size.pdf" target="_new">increase the monitoring capacity of YOMP</a>.';
        }

        bootbox.alert({
            animate:    false,
            message:    '<p>' + body + '</p><div class="alert alert-danger">' + message + '</div>',
            title:      title
        });
    };

    YOMPUI.utils.modalWarning = function(title, message, callback) {
        YOMPUI.utils.throb.stop();

        bootbox.dialog({
            message: '<p class="bg-info">' + message + '</p>',
            title: title,
            buttons: {
                main: {
                    label:      "OK",
                    className:  "btn-primary",
                    callback:   callback
                }
            }
        });
    };

    /**
     * localStorage interface
     */
    YOMPUI.utils.store = {
        set: function(k, v) {
            // some sanity checks for debugging
            if (k === 'user' && v) {
                if (! v.apiKey) {
                    throw new Error('Cannot save user without an API key!');
                }
                if (v.password) {
                    throw new Error('User should never be saved with a password hash!');
                }
            }
            if (typeof v === 'string') {
                localStorage.setItem(k, v);
            } else {
                localStorage.setItem(k, JSON.stringify(v));
            }
        },
        get: function(k) {
            var item = localStorage.getItem(k),
                result;
            if (! item) return;
            try {
                result = JSON.parse(item);
            } catch (e) {
                result = item;
            }
            return result;
        },
        clear: function(k) {
            localStorage.removeItem(k);
        },
        clearAll: function() {
            localStorage.clear();
        },
        /* clears out the necessary stuff from localStorage for logout */
        logout: function() {
            YOMPUI.utils.store.clear('apiKey');
        }
    };

    YOMPUI.utils.linkTo = function(page) {
        var sep = page.match(/^\//) ? '' : '/';
        return NTA.baseUrl + sep + page;
    };

    /**
     * Go to another page
     */
    YOMPUI.utils.go = function(where, hardReset) {
        hardReset = true;   // TODO: remove when backbone views work together better
        if (hardReset) {
            window.location.href = YOMPUI.utils.linkTo(where);
        } else {
            YOMPUI.router.navigate(where, true);
        }
    };

    /**
     * Global full-screen loading throbber
     */
    YOMPUI.utils.throb = {
        _throbbing: false,

        start: function(message) {
            var $throb = $('.loading-throbber'),
                $msg = $throb.find('div span');

            YOMPUI.utils.throb.stop();

            $msg.addClass('off');

            if (this._throbbing) {
                return;
            }
            this._throbbing = true;

            window.scrollTo(0, 0);
            windowOnscroll = window.onscroll;
            window.onscroll = function () { window.scrollTo(0, 0); };

            if(message) {
                $msg.html(message);
                $msg.removeClass('off');
            }
            $throb.removeClass('off');
        },

        message: function(message) {
            var $throb = $('.loading-throbber');
                $msg = $throb.find('div span');
            $msg.html(message);
        },

        stop: function() {
            var $throb = $('.loading-throbber');
            $throb.addClass('off');
            window.onscroll = windowOnscroll;
            this._throbbing = false;
        }
    };

    /**
     * Base64 encoding, used in YOMPAPI.js.
     *  Could possibly be legacy, we now have crypto-js eaisly loadable,
     *  might be able to move this out.
     */
    YOMPUI.utils.Base64 = {
        // private property
        _keyStr : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",

        // public method for encoding
        encode : function (input) {
            var output = "";
            var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
            var i = 0;

            input = this._utf8_encode(input);

            while (i < input.length) {
                chr1 = input.charCodeAt(i++);
                chr2 = input.charCodeAt(i++);
                chr3 = input.charCodeAt(i++);

                enc1 = chr1 >> 2;
                enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
                enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
                enc4 = chr3 & 63;

                if (isNaN(chr2)) {
                    enc3 = enc4 = 64;
                } else if (isNaN(chr3)) {
                    enc4 = 64;
                }

                output = output +
                    this._keyStr.charAt(enc1) + this._keyStr.charAt(enc2) +
                    this._keyStr.charAt(enc3) + this._keyStr.charAt(enc4);
            }
            return output;
        },

        // private method for UTF-8 encoding
        _utf8_encode : function (string) {
            string = string.replace(/\r\n/g,"\n");
            var utftext = "";

            for (var n = 0; n < string.length; n++) {

                var c = string.charCodeAt(n);

                if (c < 128) {
                    utftext += String.fromCharCode(c);
                }
                else if((c > 127) && (c < 2048)) {
                    utftext += String.fromCharCode((c >> 6) | 192);
                    utftext += String.fromCharCode((c & 63) | 128);
                }
                else {
                    utftext += String.fromCharCode((c >> 12) | 224);
                    utftext += String.fromCharCode(((c >> 6) & 63) | 128);
                    utftext += String.fromCharCode((c & 63) | 128);
                }
            }
            return utftext;
        }

    };

    /**
     * Append to default page title
     */
    YOMPUI.utils.title = function(msg) {
        document.title = msg + ' ' + document.title;
    };

    /**
     * Handle click on global header nav menu item: Help
     */
    YOMPUI.utils.help = {
        show : function() {
            // Remove hotfix part of version (i.e. "1.4.0" => "1.4")
            var version = YOMPUI.product.version.replace(/(\d+)\.(\d+)\.?(\d*)/,"\$1.\$2");
            // Convert URL to version specific URL
            var url = YOMPUI.msgs('site').resources.help.replace(/%version%/g, version);
            window.open(url);
        }
    };

    /**
     * Make an Anomaly Bar Chart gradient map, pass in # of slots.
     * !!! This should match display of mobile app !!!
     * Uses RGBColor and/or RGBColor from RGB lib in Dygraphs
     * @param {number} slots Integer for number of vertical slots/pixels to use.
     * @param {array} colors List of RGBColor objects, i.e.:
     *  [ {RGBColor}, {RGBColor}, ... ]
     *  These colors will be spread over and merged with each other in basic
     *  order across the # of slots provided.
     * @returns {array} List of RGBColor objects, list has "slots" length,
     *  and contains "colors", with calculated colors in between each, spread
     *  across slots evenly.
     */
    YOMPUI.utils.makeGradientMap = function(slots, colors) {
        var colorMap =          [],
            colorDivider =      Math.abs(colors.length - 2), // kill first+last
            colorIndexDelta =   parseInt(slots / (colorDivider + 1)),
            colorCnt =          0,
            i =                 0;

        // first
        colorMap[0] = colors[colorCnt];

        // middles
        for(i=colorIndexDelta; i<slots; i+=colorIndexDelta) {
            colorMap[i] = colors[++colorCnt];
        }

        // last
        colorMap[slots] = colors[colors.length - 1];

        // fill in gaps inbetween first/middle/last
        for(i=0; i<slots; i+=colorIndexDelta) {
            var current =       colorMap[i],
                target =        colorMap[i+colorIndexDelta],
                deltaRed =      Math.round((target.r - current.r) / colorIndexDelta),
                deltaGreen =    Math.round((target.g - current.g) / colorIndexDelta),
                deltaBlue =     Math.round((target.b - current.b) / colorIndexDelta);

            for(j=i; j<(i+colorIndexDelta); j++) {
                if(! colorMap[j]) {
                    var r = colorMap[j-1].r + deltaRed,
                        g = colorMap[j-1].g + deltaGreen,
                        b = colorMap[j-1].b + deltaBlue,
                        colorDef = 'rgb(' + r + ',' + g + ',' + b + ')';

                    colorMap[j] = new RGBColor(colorDef);
                }
            }
        }

        return colorMap.reverse();
    };

    /**
     * Split a timestamp string into a part list. Also accounts for JS month
     *  numbers being off by 1.
     * @method
     * @param {string} timestamp Timestamp string "YYYY-MM-DD HH:MM:SS"
     * @returns {array} List of datetime parts [ YYYY, MM, DD, HH, MM, SS ]
     */
    YOMPUI.utils.getDateParts = function(timestamp) {
        var parts = timestamp.split(/[ -/:]/);
        parts[1]--; // js months off by 1
        return parts;
    };

    /**
     * Join date parts into a JS UTC Date() object instance
     * @method
     * @param {array} List of datetime parts [ YYYY, MM, DD, HH, MM, SS ]
     * @returns {object} JS UTC Date object instance
     */
    YOMPUI.utils.getUTCDate = function(dateParts) {
        return new Date(Date.UTC.apply(null, dateParts));
    };

    /**
     * Parse timestamp string into JS UTC Date object instance
     * @method
     * @param {string} timestamp Timestamp string "YYYY-MM-DD HH:MM:SS"
     * @returns {object} JS UTC Date object instance
     */
    YOMPUI.utils.getUTCDateFromTimestamp = function(timestamp) {
        return YOMPUI.utils.getUTCDate(
            YOMPUI.utils.getDateParts(timestamp)
        );
    };

    /**
     * Get a timestamp string from a JS UTC Date object instance
     * @method
     * @param {object} utcDateObj JS UTC Date Object instance
     * @returns {string} Timestamp string "YYYY-MM-DD HH:MM:SS"
     */
    YOMPUI.utils.getUTCTimestamp = function(utcDateObj) {
        var year =      utcDateObj.getUTCFullYear(),
            month =     utcDateObj.getUTCMonth(),
            day =       utcDateObj.getUTCDate(),
            hour =      utcDateObj.getUTCHours(),
            min =       utcDateObj.getUTCMinutes(),
            sec =       utcDateObj.getUTCSeconds(),
            result =    null;

        month++;

        if(month.toString().length === 1) {
            month = '0' + month.toString();
        }
        if(day.toString().length === 1) {
            day = '0' + day.toString();
        }
        if(hour.toString().length === 1) {
            hour = '0' + hour.toString();
        }
        if(min.toString().length === 1) {
            min = '0' + min.toString();
        }
        if(sec.toString().length === 1) {
            sec = '0' + sec.toString();
        }

        result = [ year, month, day ].join('-') + ' ' +
                 [ hour, min, sec ].join(':');

        return result;
    };

})(jQuery);
