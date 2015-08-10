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

package com.YOMPsolutions.YOMP.mobile.instance;

import android.app.ActionBar.Tab;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.support.v4.app.Fragment;

import com.numenta.core.data.AggregationType;
import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.HourDayWeekActivity;
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.SortBarFragment;
import com.YOMPsolutions.YOMP.mobile.SortOrder;
import com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants;
import com.YOMPsolutions.YOMP.mobile.tutorial.TutorialActivity;
import com.numenta.core.utils.Log;

/**
 * <p>
 * This activity will be launched when the application starts.
 * </p>
 * <p>
 * The basic application layout is based on a ViewPager connected to ActionBar
 * Tabs where the user can change between 3 different views:
 * </p>
 * <ul>
 * <li>Hour</li>
 * <li>Day</li>
 * <li>Week</li>
 * </ul>
 * <p>
 * Where each View is managed by its own Fragment.
 * </p>
 *
 * @see MetricPageFragment
 */
public class InstanceListActivity extends HourDayWeekActivity implements
        SortBarFragment.SortBarListener {
    private static final String TAG = InstanceListActivity.class.getCanonicalName();

    @Override
    protected Fragment createTabFragment(Tab tab) {
        InstanceListFragment fragment = new InstanceListFragment();
        Bundle args = new Bundle();
        AggregationType type = (AggregationType) tab.getTag();
        args.putSerializable(AggregationType.class.getCanonicalName(), type);
        fragment.setArguments(args);
        return fragment;
    }

    @Override
    public void onSortChanged(int sortByValue) {
        switch (sortByValue) {
            case R.id.sortByAnomalies:
                Log.i(TAG, "{TAG:ANDROID.ACTION.SORT.ANOMALIES}");
                YOMPApplication.setSort(SortOrder.Anomaly);
                break;
            case R.id.sortByName:
                Log.i(TAG, "{TAG:ANDROID.ACTION.SORT.NAME}");
                YOMPApplication.setSort(SortOrder.Name);
                break;
            default:
                // TODO Sort by 'Unknown'
                Log.i(TAG, "{TAG:ANDROID.ACTION.SORT.UNKNOWN}");
                YOMPApplication.setSort(SortOrder.Unknown);
                break;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Check if we should show the tutorial page
        SharedPreferences pref = PreferenceManager
                .getDefaultSharedPreferences(getApplicationContext());
        boolean skipTutorial = pref.getBoolean(PreferencesConstants.PREF_SKIP_TUTORIAL, false);
        if (!skipTutorial) {
            Intent myIntent = new Intent(this, TutorialActivity.class);
            startActivity(myIntent);
            overridePendingTransition(0, R.anim.fadeout_animation);
        }
    }

    @Override
    protected int getResourceView() {
        return R.layout.activity_instance_list;
    }
}
