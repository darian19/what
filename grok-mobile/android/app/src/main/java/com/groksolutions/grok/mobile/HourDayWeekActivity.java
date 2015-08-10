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

package com.YOMPsolutions.YOMP.mobile;

import com.google.android.gms.analytics.HitBuilders;
import com.google.android.gms.analytics.Tracker;

import com.numenta.core.data.AggregationType;

import android.app.ActionBar;
import android.app.ActionBar.Tab;
import android.app.FragmentTransaction;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentPagerAdapter;
import android.support.v4.view.ViewPager;

import java.util.Locale;

/**
 * <p>
 * Based activity whose all other activities must inherit to show a fixed action bar and menu
 * </p>
 * <p>
 * The basic application layout is based on a ViewPager connected to ActionBar Tabs where the user
 * can change between 3 different views:
 * </p>
 * <ul>
 * <li>Hour</li>
 * <li>Day</li>
 * <li>Week</li>
 * </ul>
 * <p>
 * Where each View is managed by its own Fragment.
 * <ul>
 * <li>Override {@link #createTabFragment(Tab)} to create your own fragment for each {@link Tab}
 * <li>Override {@link #getResourceView()} to supply the view layout. The layout must contain
 * {@link ViewPager} whose id is {@link R.id.pager} to host all other {@link Fragment}s.
 * </ul>
 * </p>
 *
 * @see com.YOMPsolutions.YOMP.mobile.YOMPActivity
 */
@SuppressWarnings("deprecation")
public abstract class HourDayWeekActivity extends YOMPActivity implements
        ActionBar.TabListener {

    /**
     * Override {@link #getResourceView()} to supply the view layout.
     *
     * @return ID for an XML layout resource to be used as the
     * top level view (e.g., R.layout.activity_instance_list)
     */
    protected abstract int getResourceView();

    /**
     * Create {@link android.support.v4.app.Fragment} to be associated with the given {@link
     * android.app.ActionBar.Tab}
     *
     * @param tab The {@link android.app.ActionBar.Tab} for which the
     *            {@link android.support.v4.app.Fragment} will be created.
     *            Usually the tab is associated with a specific {@link com.numenta.core.data.AggregationType},
     *            use {@link android.app.ActionBar.Tab#getTag()} to get the {@link
     *            com.numenta.core.data.AggregationType}
     * @return The {@link android.support.v4.app.Fragment} for this tab
     */
    protected abstract Fragment createTabFragment(Tab tab);


    /**
     * The {@link ViewPager} that will host the section contents.
     */
    ViewPager _viewPager;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(getResourceView());

        // Set up the action bar.
        final ActionBar actionBar = getActionBar();
        actionBar.setNavigationMode(ActionBar.NAVIGATION_MODE_TABS);
        actionBar.setDisplayShowTitleEnabled(false);

        Locale l = Locale.getDefault();

        // For each of the sections in the app, add a tab to the action bar.
        // Add the "Fragment" class to the tab's tag. The tab's "Fragment" will
        // be created using this class

        // Hour Page
        actionBar.addTab(actionBar.newTab()
                .setText(getString(R.string.title_tab_hour).toUpperCase(l))
                .setTabListener(this).setTag(AggregationType.Hour));

        // Day Page
        actionBar.addTab(actionBar.newTab()
                .setText(getString(R.string.title_tab_day).toUpperCase(l))
                .setTabListener(this).setTag(AggregationType.Day));

        // Week Page
        actionBar.addTab(actionBar.newTab()
                .setText(getString(R.string.title_tab_week).toUpperCase(l))
                .setTabListener(this).setTag(AggregationType.Week));

        // Create the fragment adapter that will return a fragment based on the
        // Fragment class attached to the tab's tag object
        final FragmentPagerAdapter pagerAdapter = new FragmentPagerAdapter(
                getSupportFragmentManager()) {

            final Fragment[] _fragments = new Fragment[3];

            @Override
            public Fragment getItem(int position) {
                Tab tab = actionBar.getTabAt(position);
                if (tab != null) {
                    if (_fragments[position] == null) {
                        _fragments[position] = createTabFragment(tab);
                    }
                }
                return _fragments[position];
            }

            @Override
            public int getCount() {
                return actionBar.getTabCount();
            }
        };

        // Set up the ViewPager with the sections adapter.
        _viewPager = (ViewPager) findViewById(R.id.pager);
        _viewPager.setAdapter(pagerAdapter);

        // Keep all pages in memory
        _viewPager.setOffscreenPageLimit(2);

        // When swiping between different sections, select the corresponding
        // tab. We can also use ActionBar.Tab#select() to do this if we have
        // a reference to the Tab.
        _viewPager
                .setOnPageChangeListener(new ViewPager.SimpleOnPageChangeListener() {
                    @Override
                    public void onPageSelected(int position) {
                        actionBar.setSelectedNavigationItem(position);
                    }
                });
    }

    void restoreTabSelection() {
        AggregationType aggregation = YOMPApplication.getAggregation();
        final ActionBar actionBar = getActionBar();
        if (actionBar == null) {
            return;
        }
        for (int i = 0; i < actionBar.getTabCount(); i++) {
            Tab tab = actionBar.getTabAt(i);
            if (aggregation.equals(tab.getTag())) {
                actionBar.selectTab(tab);
                break;
            }
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        restoreTabSelection();
    }

    @Override
    public void onTabSelected(ActionBar.Tab tab, FragmentTransaction fragmentTransaction) {
        // When the given tab is selected, switch to the corresponding page in
        // the ViewPager.
        if (_viewPager != null) {
            _viewPager.setCurrentItem(tab.getPosition());
            AggregationType aggregationType = (AggregationType) tab.getTag();
            // Update Global State with new aggregation
            YOMPApplication.setAggregation(aggregationType);
            Tracker tracker = YOMPApplication.getInstance().getGoogleAnalyticsTracker();
            tracker.setPage(aggregationType.name());
            tracker.send(new HitBuilders.AppViewBuilder().build());
        }
    }

    @Override
    public void onTabUnselected(ActionBar.Tab tab, FragmentTransaction fragmentTransaction) {
        // Do nothing
    }

    @Override
    public void onTabReselected(ActionBar.Tab tab,
            FragmentTransaction fragmentTransaction) {
        // Do nothing
    }
}
