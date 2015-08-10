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

package com.numenta.taurus.instance;

import com.numenta.core.preference.PreferencesConstants;
import com.numenta.core.ui.chart.AnomalyListAdapter;
import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.NotificationUtils;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.TaurusBaseActivity;
import com.numenta.taurus.preference.TaurusPreferenceConstants;
import com.numenta.taurus.tutorial.TutorialActivity;

import android.app.ActionBar;
import android.app.NotificationManager;
import android.app.SearchManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.Resources;
import android.graphics.Color;
import android.os.AsyncTask;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.support.annotation.NonNull;
import android.support.v4.view.MenuItemCompat;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.SearchView;
import android.widget.TextView;

/**
 * <p>
 * This activity will be launched when the application starts.
 * </p>
 */
public class InstanceListActivity extends TaurusBaseActivity {

    private InstanceListFragment _listFragment;

    private RadioGroup _favorites;

    private static final String TAG = "InstanceListActivity";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        final SharedPreferences pref = PreferenceManager
                .getDefaultSharedPreferences(getApplicationContext());

        // Create content from resource
        setContentView(R.layout.activity_instance_list);

        // Get ListFragment
        _listFragment = (InstanceListFragment) getFragmentManager()
                .findFragmentById(R.id.instance_list_fragment);

        // Add Filter menu
        ActionBar actionBar = getActionBar();
        if (actionBar != null) {
            actionBar.setHomeButtonEnabled(false);
            actionBar.setDisplayShowCustomEnabled(true);
            actionBar.setCustomView(R.layout.actionbar_filter);
            _favorites = (RadioGroup) actionBar.getCustomView().findViewById(R.id.filter);
            if (_favorites != null) {
                _favorites.setOnCheckedChangeListener(new RadioGroup.OnCheckedChangeListener() {
                    @Override
                    public void onCheckedChanged(RadioGroup group, int checkedId) {
                        if (checkedId == R.id.filter_favorites) {
                            clearNotifications();
                            _listFragment.filterFavorites();
                        } else {
                            _listFragment.clearFilter();
                        }
                        // Write the new viewState to the preferences
                        pref.edit().putInt(TaurusPreferenceConstants.PREF_LAST_VIEW_STATE,
                                checkedId).apply();
                    }
                });
                int checkedId = R.id.filter_none;
                try {
                    checkedId = pref.getInt(TaurusPreferenceConstants.PREF_LAST_VIEW_STATE,R.id.filter_none);
                } catch (ClassCastException e) {
                    // Remove old preference value
                    pref.edit().remove(TaurusPreferenceConstants.PREF_LAST_VIEW_STATE).apply();
                }
                RadioButton button = (RadioButton) _favorites.findViewById(checkedId);
                if (button != null) {
                    button.setChecked(true);
                }
            }
        }
        // Handle search queries
        if (getIntent() != null) {
            handleIntent(getIntent());
        }
        // Check if we should show the tutorial page
        boolean skipTutorial = pref.getBoolean(PreferencesConstants.PREF_SKIP_TUTORIAL, false);
        if (!skipTutorial) {
            Intent myIntent = new Intent(this, TutorialActivity.class);
            startActivity(myIntent);
            overridePendingTransition(0, R.anim.fadeout_animation);
        }

    }

    @Override
    public void onBackPressed() {
        if (_favorites.getCheckedRadioButtonId() == R.id.filter_favorites) {
            clearNotifications();
            RadioButton b = (RadioButton) _favorites.findViewById(R.id.filter_none);
            b.setChecked(true);
        } else {
            super.onBackPressed();
        }
    }

    /**
     * Clear any notifications
     */
    private void clearNotifications() {
        AsyncTask.execute(
                new Runnable() {
                   @Override
                   public void run() {
                       NotificationUtils.resetGroupedNotifications();
                       ((NotificationManager) getSystemService(NOTIFICATION_SERVICE)).cancelAll();

                   }
                }
        );
    }

    /**
     * If the activity was started with an intent, such as {@link Intent#ACTION_SEARCH},
     * perform the action expressed in the intent.
     *
     * @param intent The intent to process
     * @see Intent#ACTION_SEARCH
     */
    private void handleIntent(@NonNull Intent intent) {
        // Handle "Search" intents
        if (Intent.ACTION_SEARCH.equals(intent.getAction())) {
            // SearchManager.QUERY is the key that a SearchManager will use to send a query string
            // to an Activity.
            String query = intent.getStringExtra(SearchManager.QUERY);
            _listFragment.applyFilter(query);
        }
        if (TaurusApplication.ACTION_SHOW_NOTIFICATION_LIST.equals(intent.getAction())) {
            clearNotifications();
            if (_favorites.getCheckedRadioButtonId() == R.id.filter_none) {
                RadioButton b = (RadioButton) _favorites.findViewById(R.id.filter_favorites);
                b.setChecked(true);
            }
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        handleIntent(intent);
    }


    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        boolean res = super.onCreateOptionsMenu(menu);

        // Get the SearchView and set the searchable configuration
        MenuItem searchItem = menu.findItem(R.id.menu_search);
        searchItem.setVisible(true);
        final SearchView searchView = (SearchView) searchItem.getActionView();
        if (searchView != null) {
            configureSearchView(searchView);
        }

        MenuItemCompat.setOnActionExpandListener(searchItem, new MenuItemCompat.OnActionExpandListener() {
            @Override
            public boolean onMenuItemActionCollapse(MenuItem item) {
                ((AnomalyListAdapter)_listFragment.getListAdapter()).sort(
                        DataUtils.<InstanceAnomalyChartData>getSortByAnomalyComparator());
                if (_favorites.getCheckedRadioButtonId() == R.id.filter_none) {
                    _listFragment.clearFilter();
                } else {
                    _listFragment.filterFavorites();
                }
                _listFragment.showHeaders(true);
                return true;
            }

            public boolean onMenuItemActionExpand(MenuItem item) {
                ((AnomalyListAdapter)_listFragment.getListAdapter()).sort(
                        DataUtils.<InstanceAnomalyChartData>getSortByNameComparator());
                _listFragment.clearFilter();
                _listFragment.showHeaders(false);
                return true;
            }
        });

        return res;
    }

    private void configureSearchView(@NonNull final SearchView searchView) {
        SearchManager searchManager = (SearchManager) getSystemService(Context.SEARCH_SERVICE);
        // Assumes current activity is the searchable activity
        searchView.setSearchableInfo(searchManager.getSearchableInfo(getComponentName()));

        // Handle query events
        searchView.setOnQueryTextListener(new SearchView.OnQueryTextListener() {
            @Override
            public boolean onQueryTextSubmit(String query) {
                // Hide Keyboard on submit
                InputMethodManager imm = (InputMethodManager)
                        searchView.getContext().getSystemService(Context.INPUT_METHOD_SERVICE);
                if (imm != null) {
                    imm.hideSoftInputFromWindow(searchView.getWindowToken(), 0);
                }

                return true;
            }

            @Override
            public boolean onQueryTextChange(String newText) {
                // Filter list as the user types
                _listFragment.applyFilter(newText);
                return true;
            }
        });

        // FIXME: Android does not support styling the search view across all versions.
        // For now, "peek" into internal API to make the appropriate changes to the SearchView.
        // In the future we should use the official android API to customize the SearchView widget.
        // See android.R.layout.search_view for the layout we are "peeking". It is no guarantee it
        // will work on all public android versions and/or OEM customizations.
        // This HACK is only valid for the POC phase. We should find a better solution before releasing
        Resources resources = searchView.getResources();

        // Style search box and text
        int searchPlateId = resources.getIdentifier("android:id/search_plate", null, null);
        View searchPlate = searchView.findViewById(searchPlateId);
        if (searchPlate != null) {
            int searchTextId = resources.getIdentifier("android:id/search_src_text", null, null);
            TextView searchText = (TextView) searchPlate.findViewById(searchTextId);
            if (searchText != null) {
                searchPlate.setBackgroundResource(android.R.drawable.editbox_background);
                searchText.setPadding(5, 0, 0, 0);
                searchText.setTextColor(Color.BLACK);
                searchText.setHintTextColor(Color.LTGRAY);
            }
        }
    }
}
