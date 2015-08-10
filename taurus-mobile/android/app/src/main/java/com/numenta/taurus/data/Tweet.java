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

package com.numenta.taurus.data;

import com.numenta.core.utils.DataUtils;

import java.io.Serializable;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Helper class representing one "tweet" record
 */
public class Tweet implements Serializable {

    final private String _id;

    final private long _created;

    final private long _aggregated;

    final private String _userId;

    final private String _userName;

    final private String _text;

    final private boolean _hasLinks;

    final private String _cannonicalText;

    // Match "RT @tags" from the beginning of the text.
    private static final Pattern RT_REGEX = Pattern
            .compile("^\\s*RT\\s+(@[a-zA-Z][_a-zA-Z0-9]*\\s*)*");

    // From left side – Match @, #, $ up to colon symbol
    private static final Pattern LEFT_HASHTAG_UP_TO_COLON_REGEX = Pattern
            .compile("^\\s*([@#$][a-zA-Z][_a-zA-Z0-9]*\\s?)*:\\s*");

    // From left side – Match @, #, $ up to last
    private static final Pattern LEFT_HASHTAG_UP_TO_LAST_REGEX = Pattern
            .compile("^\\s*([@#$][a-zA-Z][_a-zA-Z0-9]*\\s*){2,}");

    // From right side – Match @, #, $ when followed by letter, not a number
    private static final Pattern RIGHT_HASHTAG_REGEX = Pattern
            .compile("\\s*([@#$][a-zA-Z][_a-zA-Z0-9]*\\s*)+\\s*$");

    // Match "http" or "https" URLs
    private static final Pattern LINKS_REGEX = Pattern.compile("\\s*https?:\\/\\/\\S+\\s*");

    // Match "..." at the end of the text
    private static final Pattern DOT_DOT_DOT_REGEX = Pattern.compile("\\s*\\.{2,}\\s*$");

    // Match 2 or more spaces
    private static final Pattern TWO_OR_MORE_SPACES_REGEX = Pattern.compile("\\s+");

    private int _aggregatedCount;

    private int _retweetCount;

    private int _retweetTotal;

    public Tweet(String id, long aggregated, long created, String userId, String userName,
            String text, int retweetTotal) {
        _userName = userName;
        _userId = userId;
        _created = created;
        // Make sure aggregated values are rounded to closest 5 minute interval
        _aggregated = DataUtils.floorTo5minutes(aggregated);
        _id = id;
        _retweetTotal = retweetTotal;

        // Clean up HTML encoded text
        _text = text.replaceAll("&amp;", "&")
                .replaceAll("&quot;", "\"")
                .replaceAll("&lt;", "<")
                .replaceAll("&gt;", ">");

        // Remove duplicate tweets using specific set of rules. See "getCannonicalText" for rules
        String rawText = _text;

        // Remove "..."
        rawText = DOT_DOT_DOT_REGEX.matcher(rawText).replaceAll("");

        // Remove all links
        Matcher matcher = LINKS_REGEX.matcher(rawText);
        if (_hasLinks = matcher.find()) {
            rawText = matcher.replaceAll(" ");
        }

        // Remove "RT" re-tweets
        rawText = RT_REGEX.matcher(rawText).replaceAll(" ");

        // Remove Hash and dollar tags from the left
        matcher = LEFT_HASHTAG_UP_TO_COLON_REGEX.matcher(rawText);
        if (matcher.find()) {
            // Remove everything up to the colon
            rawText = matcher.replaceAll(" ");
        } else {
            // Keep last hash tag
            rawText = LEFT_HASHTAG_UP_TO_LAST_REGEX.matcher(rawText).replaceAll("$1");
        }
        // Remove hash tags from the right
        rawText = RIGHT_HASHTAG_REGEX.matcher(rawText).replaceAll(" ");

        // Remove line feeds and extra spaces
        rawText = TWO_OR_MORE_SPACES_REGEX.matcher(rawText).replaceAll(" ");
        _cannonicalText = rawText.replaceAll("\\n|\\r", "").trim();

    }

    /**
     * Returns {@code true} if the original tweet has any links
     */
    public boolean hasLinks() {
        return _hasLinks;
    }

    /**
     * Return twitter text without retweets (RT) and other decorators. The current logic is:
     *
     * <ul>
     * <li> Remove "RT " from the beginning of the text up to the colon.</li>
     * <li> Remove all links from the text.</li>
     * <li> From left side – remove @, #, $ up to colon symbol.</li>
     * <li> If no colon – remove @, #, $ when there are multiple in a row (up to last one).</li>
     * <li>From right side – remove @, #, $ (only remove $ when followed by letter, not a number)
     * up to text</li>
     * </ul>
     * <p>
     * For example:
     * <ol>
     * <li>
     * <b>Original:</b> "RT @Kelly_Evans: Salesforce $CRM just reopened over at Post 6 and surging
     * 13% on BBG reports of possible suitors @NYSE"
     * <br>
     * <b>Condensed:</b> "Salesforce $CRM just reopened over at Post 6 and surging 13% on BBG
     * reports of possible suitors"
     * </li>
     * <li>
     * <b>Original:</b> "RT @hblodget: Someone offered to buy Salesforce! RT@SAI: Salesforce
     * has hired advisors to fend off takeover offers $CRM http://t.co/DGfSez"
     * <br>
     * <b>Condensed: </b>"Someone offered to buy Salesforce! RT@SAI: Salesforce has hired
     * advisors to fend off takeover offers $CRM <b>link</b>"
     * </li>
     * <li>
     * <b>Original:</b> "RT @BloombergDeals: Breaking on Bloomberg: http://t.co/nuMtaw43j is
     * said to hire bankers to field takeover interest. Terminal link: http://t.co/ssfSEca3rk"
     * <br>
     * <b>Condensed:</b> "Breaking on Bloomberg: is said to hire bankers to field takeover
     * interest. Terminal link: <b>link</b>"
     * </li>
     * <li>
     * <b>Original:</b> "RT @OptionHawk: $CRM takeover talks, whoa!"
     * <br>
     * <b>Condensed:</b> "$CRM takeover talks, whoa!"
     * </li>
     * <li>
     * <b>Original:</b> "$SUTI Has now seen 400% gains in the past 2 weeks!
     * Special update: http://t.co/DGfSez3QA $ESRX $COST $BIIB"
     * <br>
     * <b>Condensed:</b> "Has now seen 400% gains in the past 2 weeks! Special update: <b>link</b>"
     * </li>
     * <li>
     * <b>Original:</b> "MCD McDonalds Corp. Volume http://t.co/sfda3SDA $MCD $DG $MRO $FCEL
     * $MCD #stock #tradeideas"
     * <br>
     * <b>Condensed:</b> "MCD McDonalds Corp. Volume <b>link</b>"
     * </li>
     * <li>
     * <b>Original:</b> "RT @wbznewsradio: NEW: @CharterCom to buy @TWC for $53.33 billion in
     * cash-and-stock deal. Charter will also buy @BrighHouseNow for $10B+"
     * <br>
     * <b>Condensed:</b> "NEW: @CharterCom to buy @TWC for $53.33 billion in cash-and-stock
     * deal. Charter will also buy @BrighHouseNow for $10B+"
     * </li>
     * </ol>
     * </p>
     */
    public String getCanonicalText() {
        return _cannonicalText;
    }

    public String getId() {
        return _id;
    }

    public long getAggregated() {
        return _aggregated;
    }

    public long getCreated() {
        return _created;
    }

    public String getUserId() {
        return _userId;
    }

    public String getUserName() {
        return _userName;
    }

    public String getText() {
        return _text;
    }

    public int getAggregatedCount() {
        return _aggregatedCount;
    }

    public void setAggregatedCount(int aggregatedCount) {
        _aggregatedCount = aggregatedCount;
    }

    public int getRetweetCount() {
        return _retweetCount;
    }

    public void setRetweetCount(int count) {
        _retweetCount = count;
    }

    public int getRetweetTotal() {
        return _retweetTotal;
    }
}
