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

import com.numenta.core.ui.chart.AnomalyChartData;
import com.numenta.taurus.R;
import com.numenta.taurus.TaurusApplication;
import com.numenta.taurus.chart.AbstractAnomalyChartFragment;
import com.numenta.taurus.chart.AnomalyChartView;

import android.app.Activity;
import android.content.res.TypedArray;
import android.os.Bundle;
import android.util.AttributeSet;
import android.view.ContextMenu;
import android.view.LayoutInflater;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

public class InstanceAnomalyChartFragment extends AbstractAnomalyChartFragment {

    private boolean _showContextMenu;

    private boolean _collapsed;

    @SuppressWarnings("RedundantNoArgConstructor")
    public InstanceAnomalyChartFragment() {

    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
            Bundle savedInstanceState) {
        View view = super.onCreateView(inflater, container, savedInstanceState);
        // Show Context menu
        if (_showContextMenu && view != null) {
            registerForContextMenu(view);
        }
        return view;
    }

    protected void updateName(final View parent, final AnomalyChartData data) {
        final TextView nameView = (TextView) parent.findViewById(R.id.name);
        final TextView tickerView = (TextView) parent.findViewById(R.id.ticker);

        if (nameView != null && tickerView != null) {
            if (data == null) {
                nameView.setText(null);
                nameView.setSelected(false);
                tickerView.setText(null);
                tickerView.setSelected(false);
            } else {
                final InstanceAnomalyChartData instance = (InstanceAnomalyChartData) data;
                final CharSequence oldName = nameView.getText();
                if (!oldName.equals(instance.getName())) {
                    // Update name
                    nameView.setText(instance.getName());
                    // Update ticker
                    tickerView.setText(instance.getTicker());
                }
            }
            parent.forceLayout();
        }
    }

    @Override
    public void onCreateContextMenu(ContextMenu menu, View v,
            ContextMenu.ContextMenuInfo menuInfo) {
        super.onCreateContextMenu(menu, v, menuInfo);
        InstanceAnomalyChartData instance = (InstanceAnomalyChartData) _chartData;

        // Show Context menu with "Add/Remove Favorites" depending on the instance selected
        if (!TaurusApplication.isInstanceFavorite(instance.getId())) {
            menu.add(0, R.id.menu_add_favorite, 0, R.string.menu_add_favorite);
        } else {
            menu.add(0, R.id.menu_remove_favorite, 0, R.string.menu_remove_favorite);
        }
    }

    @Override
    public boolean performLongClick(final View view) {
        return view.showContextMenu();
    }

    @Override
    public boolean onContextItemSelected(MenuItem item) {
        InstanceAnomalyChartData instance = (InstanceAnomalyChartData) _chartData;

        switch (item.getItemId()) {
            case R.id.menu_add_favorite:
                TaurusApplication.addInstanceToFavorites(instance.getId());
                return true;
            case R.id.menu_remove_favorite:
                TaurusApplication.removeInstanceFromFavorites(instance.getId());
                return true;
        }
        return super.onContextItemSelected(item);
    }

    @Override
    protected int getResourceView() {
        return R.layout.fragment_instance_anomaly_chart;
    }

    @Override
    public void onInflate(Activity activity, AttributeSet attrs, Bundle savedInstanceState) {
        super.onInflate(activity, attrs, savedInstanceState);
        // Get fragment arguments
        TypedArray attributes = activity.obtainStyledAttributes(attrs,
                R.styleable.InstanceAnomalyChartFragment);
        try {
            // Whether or not to show the context menu
            _showContextMenu = attributes.getBoolean(
                    R.styleable.InstanceAnomalyChartFragment_showContextMenu, true);
        } finally {
            if (attributes != null) {
                attributes.recycle();
            }
        }
    }

    protected void updateChart(AnomalyChartView chart, AnomalyChartData data) {
        chart.setData(_collapsed ? ((InstanceAnomalyChartData)data).getCollapsedData() : data.getData());
        chart.setSelectedTimestamp(getSelectedTimestamp());
    }

    /**
     * Set whether or not to collapse the time for this view. If {@code true} the view will
     * collapse the the time based on the current market calendar.
     *
     * @see com.numenta.taurus.TaurusApplication#getMarketCalendar()
     */
    public void setCollapsed(boolean collapsed) {
        if (_collapsed != collapsed) {
            _collapsed = collapsed;
            update();
        }
    }
}
