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

package com.YOMPsolutions.YOMP.mobile.tutorial;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences.Editor;
import android.os.Bundle;
import android.os.Handler;
import android.preference.PreferenceManager;
import android.support.v4.app.FragmentActivity;
import android.support.v4.content.LocalBroadcastManager;
import android.support.v4.view.PagerAdapter;
import android.support.v4.view.ViewPager;
import android.support.v4.view.ViewPager.OnPageChangeListener;
import android.view.View;
import android.widget.Button;
import android.widget.Toast;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.R;
import com.YOMPsolutions.YOMP.mobile.preference.PreferencesConstants;
import com.YOMPsolutions.YOMP.mobile.service.YOMPDataSyncService;
import com.numenta.core.service.DataSyncService;

/**
 * Displays the tutorial as {@link ViewPager} where the user can flip between the tutorial pages
 */
public class TutorialActivity extends FragmentActivity {

    int _instances;
    int _metrics;
    int _remaining;
    private PagerAdapter _pagerAdapter;
    private Button _tutorialButton;
    private boolean _done;

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.FragmentActivity#onStart()
     */
    @Override
    protected void onStart() {
        // TODO Auto-generated method stub
        super.onStart();
        YOMPApplication.setActivityLastUsed();
        YOMPApplication.incrementActivityCount();
        // Cache last metric change event while tutorial is active
        LocalBroadcastManager.getInstance(this).registerReceiver(
                _metricChangedReceiver,
                new IntentFilter(DataSyncService.METRIC_CHANGED_EVENT));
        _remaining = _instances = _metrics = 0;
    }

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.FragmentActivity#onStop()
     */
    @Override
    protected void onStop() {
        super.onStop();
        YOMPApplication.setActivityLastUsed();
        YOMPApplication.decrementActivityCount();
        LocalBroadcastManager.getInstance(this).unregisterReceiver(
                _metricChangedReceiver);
    }

    private final BroadcastReceiver _metricChangedReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            // Cache last metric change event while tutorial is active
            _instances = intent.getIntExtra(YOMPDataSyncService.EXTRA_NEW_INSTANCES, 0);
            _metrics = intent.getIntExtra(YOMPDataSyncService.EXTRA_NEW_METRICS, 0);
            _remaining = intent.getIntExtra(YOMPDataSyncService.EXTRA_REMAINING_TIME, 0);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Update preference to skip tutorial
        Editor prefs = PreferenceManager.getDefaultSharedPreferences(
                getApplicationContext()).edit();
        prefs.putBoolean(PreferencesConstants.PREF_SKIP_TUTORIAL, true);
        prefs.apply();

        setContentView(R.layout.activity_tutorial);
        _done = false;

        _tutorialButton = (Button) findViewById(R.id.skipTutorialButton);
        ViewPager pager = (ViewPager) findViewById(R.id.pager);

        pager.setOnPageChangeListener(new OnPageChangeListener() {
            @Override
            public void onPageSelected(int position) {
                _done = _done | _pagerAdapter.getCount() - 1 == position;
                if (_done) {
                    _tutorialButton.setText(R.string.tutorial_done);
                } else {
                    _tutorialButton.setText(R.string.skip_tutorial);
                }
            }

            @Override
            public void onPageScrolled(int position, float positionOffset, int positionOffsetPixels) {
                // Ignore
            }

            @Override
            public void onPageScrollStateChanged(int state) {
                // Ignore
            }
        });
        _pagerAdapter = new TutorialPagerAdapter(getSupportFragmentManager());
        pager.setAdapter(_pagerAdapter);
    }

    /**
     * Callback attached to the "Skip Tutorial" button. We close the activity whenever the user
     * clicks on this button
     */
    @SuppressWarnings("unused")
    public void onSkipTutorial(View view) {
        Toast.makeText(this, R.string.tutorial_message, Toast.LENGTH_LONG).show();

        // Fire the last metric changed event received while the tutorial was active
        if (_metrics > 0) {
            new Handler().postDelayed(new Runnable() {
                @Override
                public void run() {
                    Intent intent = new Intent(DataSyncService.METRIC_CHANGED_EVENT);
                    intent.putExtra(YOMPDataSyncService.EXTRA_NEW_METRICS, _metrics);
                    intent.putExtra(YOMPDataSyncService.EXTRA_NEW_INSTANCES, _instances);
                    intent.putExtra(YOMPDataSyncService.EXTRA_REMAINING_TIME, _remaining);
                    LocalBroadcastManager.getInstance(YOMPApplication.getContext()).sendBroadcast(
                            intent);
                }
            }, 1000);
        }
        finish();
    }
}
