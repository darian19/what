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

import com.numenta.taurus.TaurusBaseActivity;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.R;

import android.app.ActionBar;
import android.app.Fragment;
import android.os.Bundle;

import java.util.Date;

public class InstanceDetailActivity extends TaurusBaseActivity {

    public static final String INSTANCE_ID_ARG = "instance_id";
    public static final String TIMESTAMP_ARG = "timestamp";

    public String getInstanceId() {
        return getIntent().getStringExtra(INSTANCE_ID_ARG);
    }

    public long getTimestamp() {
        return getIntent().getLongExtra(TIMESTAMP_ARG, 0);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_instance_detail);
        ActionBar actionBar = getActionBar();
        if (actionBar != null) {
            actionBar.setDisplayHomeAsUpEnabled(true);
        }
    }

    /**
     * Called when a fragment is attached to the activity.
     */
    @Override
    public void onAttachFragment(Fragment fragment) {
        if (fragment instanceof InstanceDetailPageFragment) {
            InstanceDetailPageFragment instanceFragment = (InstanceDetailPageFragment) fragment;
            InstanceAnomalyChartData data = new InstanceAnomalyChartData(getInstanceId(),
                    TaurusApplication.getAggregation());
            long timestamp = getTimestamp();
            if (timestamp > 0) {
                data.setEndDate(new Date(timestamp));
            }
            instanceFragment.setRowData(data);
        }
    }
}
