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

package com.numenta.taurus.tutorial;

import com.numenta.core.preference.PreferencesConstants;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;

import android.content.SharedPreferences.Editor;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.support.v4.app.FragmentActivity;
import android.support.v4.view.PagerAdapter;
import android.support.v4.view.ViewPager;
import android.support.v4.view.ViewPager.OnPageChangeListener;
import android.view.View;
import android.widget.Button;
import android.widget.Toast;

/**
 * Displays the tutorial as {@link ViewPager} where the user can flip between the tutorial pages
 */
public class TutorialActivity extends FragmentActivity {

    private PagerAdapter _pagerAdapter;
    private ViewPager _pager;
    private Button _rightButton;
    private Button _leftButton;

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.FragmentActivity#onStart()
     */
    @Override
    protected void onStart() {
        super.onStart();
        TaurusApplication.setActivityLastUsed();
        TaurusApplication.incrementActivityCount();
    }

    /*
     * (non-Javadoc)
     * @see android.support.v4.app.FragmentActivity#onStop()
     */
    @Override
    protected void onStop() {
        super.onStop();
        TaurusApplication.setActivityLastUsed();
        TaurusApplication.decrementActivityCount();
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Update preference to skip tutorial
        Editor prefs = PreferenceManager.getDefaultSharedPreferences(
                getApplicationContext()).edit();
        prefs.putBoolean(PreferencesConstants.PREF_SKIP_TUTORIAL, true);
        prefs.apply();

        setContentView(R.layout.activity_tutorial);

        _rightButton = (Button) findViewById(R.id.tutorial_button_right);
        _leftButton = (Button) findViewById(R.id.tutorial_button_left);
        _pager = (ViewPager) findViewById(R.id.pager);
        _pager.setOnPageChangeListener(new OnPageChangeListener() {
            @Override
            public void onPageSelected(int position) {
                if (position == _pagerAdapter.getCount() - 1) {
                    _rightButton.setText(R.string.tutorial_done);
                    _leftButton.setVisibility(View.GONE);
                } else {
                    _rightButton.setText(R.string.tutorial_next);
                    _leftButton.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public void onPageScrolled(int position, float positionOffset,
                    int positionOffsetPixels) {
                // Ignore
            }

            @Override
            public void onPageScrollStateChanged(int state) {
                // Ignore
            }
        });
        _pagerAdapter = new TutorialPagerAdapter(getSupportFragmentManager());
        _pager.setAdapter(_pagerAdapter);
    }

    /**
     * Callback attached to the left button.
     */
    @SuppressWarnings("unused")
    public void onLeftButtonClick(View view) {
        finish();
    }
    /**
     * Callback attached to the right button.
     */
    @SuppressWarnings("unused")
    public void onRightButtonClick(View view) {
        int page = _pager.getCurrentItem();
        if (page < _pagerAdapter.getCount() - 1) {
            _pager.setCurrentItem(page + 1, true);
        } else {
            finish();
        }
    }
}
