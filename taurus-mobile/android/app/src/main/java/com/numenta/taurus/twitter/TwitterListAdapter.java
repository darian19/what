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

package com.numenta.taurus.twitter;

import com.numenta.core.utils.DataUtils;
import com.numenta.taurus.R;
import com.numenta.taurus.data.Tweet;

import android.content.Context;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.style.ForegroundColorSpan;
import android.text.style.StyleSpan;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.ImageView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * List adapter backed by an list of Tweets used to interface with the backend twitter
 */
public class TwitterListAdapter extends BaseAdapter {

    private static final String TAG = TwitterListAdapter.class.getSimpleName();

    final Context _context;

    final List<Tweet> _tweetList;

    final LayoutInflater _inflater;

    // Used to control data access from multiple threads
    private final ReentrantReadWriteLock _lock = new ReentrantReadWriteLock();

    private final Lock _readLock = _lock.readLock();

    private final Lock _writeLock = _lock.writeLock();

    /** Tolerate up to 30 minutes when positioning via timestamp */
    static final long TIMESTAMP_TOLERANCE = 30 * DataUtils.MILLIS_PER_MINUTE;

    /** Formatted "links" text indicating the condensed tweet text has links */
    private final SpannableStringBuilder _linkText;

    private boolean _notifyDataSetChanged = true;

    private boolean _showCondensedView;

    public void add(Tweet tweet) {
        _writeLock.lock();
        try {
            _tweetList.add(tweet);
        } finally {
            _writeLock.unlock();
        }
        if (_notifyDataSetChanged) {
            notifyDataSetChanged();
        }
    }

    public void sort(Comparator<Tweet> comparator) {
        _writeLock.lock();
        try {
            Collections.sort(_tweetList, comparator);
        } finally {
            _writeLock.unlock();
        }
        if (_notifyDataSetChanged) {
            notifyDataSetChanged();
        }
    }

    /**
     * Control whether methods that change the list ({@link #add} automatically call
     * {@link #notifyDataSetChanged}.  If set to false, caller must manually call
     * notifyDataSetChanged() to have the changes reflected in the attached view.
     *
     * The default is true, and calling notifyDataSetChanged() resets the flag to true.
     *
     * @param notifyOnChange if true, modifications to the list will automatically
     *                       call {@link #notifyDataSetChanged}
     */
    public void setNotifyDataSetChanged(boolean notifyOnChange) {
        _notifyDataSetChanged = notifyOnChange;
    }

    @Override
    public void notifyDataSetChanged() {
        _notifyDataSetChanged = true;
        super.notifyDataSetChanged();
    }

    /**
     * Whether or not show the tweet item condensed, removing the "noise" from the text. @see
     * @param showCondensedView
     */
    public void setShowCondensedView(boolean showCondensedView) {
        _showCondensedView = showCondensedView;
        notifyDataSetChanged();
    }

    static class ViewHolder {

        View groupHeader;

        TextView date;

        TextView tweetCount;

        View tweetHeader;

        TextView user;

        TextView retweetTotal;

        ImageView _retweetIcon;

        TextView retweetCount;

        TextView retweetCountCondensed;

        TextView tweetText;
    }

    public TwitterListAdapter(Context context) {
        _context = context;
        _inflater = (LayoutInflater) context.getSystemService(Context.LAYOUT_INFLATER_SERVICE);
        _tweetList = new ArrayList<Tweet>();
        _linkText = new SpannableStringBuilder(context.getString(R.string.twitter_links));
        final ForegroundColorSpan colorSpan = new ForegroundColorSpan(
                context.getResources().getColor(R.color.twitter_links));
        _linkText.setSpan(colorSpan, 0, _linkText.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
    }

    @Override
    public int getCount() {
        _readLock.lock();
        try {
            return _tweetList.size();
        } finally {
            _readLock.unlock();
        }
    }

    @Override
    public Tweet getItem(int position) {
        _readLock.lock();
        try {
            return _tweetList.get(position);
        } finally {
            _readLock.unlock();
        }
    }

    @Override
    public long getItemId(int position) {
        return position;
    }

    @Override
    public View getView(int position, View convertView, ViewGroup parent) {

        View view;
        if (convertView == null) {
            view = _inflater.inflate(R.layout.twitter_item, parent, false);

            // Cache views
            ViewHolder holder = new ViewHolder();
            holder.groupHeader = view.findViewById(R.id.group_header);
            holder.date = (TextView) holder.groupHeader.findViewById(R.id.date);
            holder.tweetCount = (TextView) holder.groupHeader.findViewById(R.id.tweet_count);

            holder.tweetHeader = view.findViewById(R.id.tweet_header);
            holder.user = (TextView) holder.tweetHeader.findViewById(R.id.user);
            holder.retweetTotal = (TextView) holder.tweetHeader.findViewById(R.id.retweet_total);
            holder.retweetCount = (TextView) holder.tweetHeader.findViewById(R.id.retweet_count);
            holder._retweetIcon = (ImageView) holder.tweetHeader.findViewById(R.id.retweet_icon);

            holder.tweetText = (TextView) view.findViewById(R.id.tweet_text);
            holder.retweetCountCondensed = (TextView) view.findViewById(
                    R.id.retweet_count_condensed);

            view.setTag(holder);
        } else {
            view = convertView;
        }
        // Bind view
        if (parent.isShown()) {
            bindView(view, position);
        }

        return view;
    }

    private void updateGroupHeader(ViewHolder holder, Tweet tweet) {
        // Make sure it is visible
        if (holder.groupHeader.getVisibility() != View.VISIBLE) {
            holder.groupHeader.setVisibility(View.VISIBLE);
        }

        holder.date.setText(String.format("%1$tl:%1$tM%1$tp", tweet.getAggregated()));
        holder.tweetCount.setText(Integer.toString(tweet.getAggregatedCount()));
    }

    private void bindView(View view, int position) {

        ViewHolder holder = (ViewHolder) view.getTag();
        Tweet tweet = getItem(position);

        // Update tweet headers
        if (position == 0) {
            // First tweet
            updateGroupHeader(holder, tweet);
        } else {
            // Only show if crossing the bucket boundary
            Tweet prev = getItem(position - 1);
            if (prev.getAggregated() != tweet.getAggregated()) {
                updateGroupHeader(holder, tweet);
            } else {
                // Within the same bucket. Hide header
                holder.groupHeader.setVisibility(View.GONE);
            }
        }
        updateTweetHeader(holder, tweet);

        // Update tweet text
        if (_showCondensedView) {
            // Make text bold on condensed view
            String text = tweet.getCanonicalText();
            SpannableStringBuilder span = new SpannableStringBuilder(text);
            span.setSpan(new StyleSpan(android.graphics.Typeface.BOLD), 0, text.length(),
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            // Add "links" text at the end
            if (tweet.hasLinks()) {
                span.append(" ").append(_linkText);
            }
            holder.tweetText.setText(span);
        } else {
            holder.tweetText.setText(tweet.getText());
        }
    }

    private void updateTweetHeader(ViewHolder holder, Tweet tweet) {
        if (_showCondensedView) {
            // Hide expanded header
            holder.tweetHeader.setVisibility(View.GONE);
            // Show condensed count to the right
            holder.retweetCountCondensed.setVisibility(View.VISIBLE);
            holder.retweetCountCondensed.setText(
                    tweet.getRetweetCount() > 1 ?
                            Integer.toString(tweet.getRetweetCount())
                            : "");
        } else {
            // Hide condensed count
            holder.retweetCountCondensed.setVisibility(View.GONE);
            // Show expanded header
            holder.tweetHeader.setVisibility(View.VISIBLE);
            holder.user.setText("@" + tweet.getUserName());
            int retweetCount = tweet.getRetweetCount();
            int retweetTotal = tweet.getRetweetTotal();

            holder.retweetCount.setText(retweetCount > 1 ? Integer.toString(retweetCount) : "");
            holder.retweetTotal.setText(retweetTotal > 1 ? Integer.toString(retweetTotal) : "");
            if (retweetCount > 1 || retweetTotal > 1) {
                holder._retweetIcon.setVisibility(View.VISIBLE);
            } else {
                holder._retweetIcon.setVisibility(View.GONE);
            }
        }
    }

    /**
     * Returns the position of the item with the maximum aggregation count whose timestamp is
     * within the given range based on the timestamp value and a default tolerance value.
     * The time range to search for the max value is [timestamp-tolerance, timestamp+tolerance].
     *
     * @param timestamp The timestamp to check (unix time)
     * @return The position of the first item or -1 if not found
     * @see #TIMESTAMP_TOLERANCE
     */
    public int getPositionByTimestamp(long timestamp) {
        int count = getCount();
        Tweet item;
        long lowerBound = timestamp - TIMESTAMP_TOLERANCE;
        long upperBound = timestamp + TIMESTAMP_TOLERANCE;
        int pos = -1;
        int maxValue = -1;
        for (int i = 0; i < count; i++) {
            item = getItem(i);
            if (item != null && item.getAggregated() >= lowerBound
                    && item.getAggregated() <= upperBound) {
                // Look for max value
                if (item.getAggregatedCount() > maxValue) {
                    maxValue = item.getAggregatedCount();
                    pos = i;
                }
            }
        }
        return pos;
    }

    /**
     * Returns the position of the item
     *
     * @return The position of the item or -1 if not found
     */
    public int getPositionByTweet(Tweet tweet) {
        _readLock.lock();
        try {
            return _tweetList.indexOf(tweet);
        } finally {
            _readLock.unlock();
        }
    }
}
