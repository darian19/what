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
import android.os.Bundle;
import android.support.v4.app.Fragment;

import com.numenta.core.data.AggregationType;
import com.YOMPsolutions.YOMP.mobile.HourDayWeekActivity;
import com.YOMPsolutions.YOMP.mobile.R;

public class InstanceDetailActivity extends HourDayWeekActivity {

    public static final String INSTANCE_ID_ARG = "instance_id";
    public static final String SELECTION_ARG = "selection";

    public String getInstanceId() {
        return getIntent().getStringExtra(INSTANCE_ID_ARG);
    }

    /*
     * (non-Javadoc)
     * @see
     * com.YOMPsolutions.YOMP.mobile.BaseActivity#createTabFragment(android.
     * app.ActionBar.Tab)
     */
    @Override
    protected Fragment createTabFragment(Tab tab) {
        InstanceDetailPageFragment fragment = new InstanceDetailPageFragment();
        AggregationType type = (AggregationType) tab.getTag();
        InstanceAnomalyChartData data = new InstanceAnomalyChartData(getInstanceId(), type);
        fragment.setRowData(data);
        Bundle args = new Bundle();
        args.putSerializable("AggregationType", type);
        fragment.setArguments(args);
        return fragment;
    }

    @Override
    protected int getResourceView() {
        return R.layout.activity_instance_detail;
    }
}
