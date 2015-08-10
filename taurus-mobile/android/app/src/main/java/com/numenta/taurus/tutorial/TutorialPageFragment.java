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


import com.numenta.taurus.R;

import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;

/**
 * Tutorial page {@link Fragment}.
 * <p>
 * The {@link TutorialActivity} will flip between the tutorial pages using this
 * fragment. Each {@code TutorialPageFragment} represents one page in the
 * tutorial. The page itself is an {@link ImageView}.
 *
 * @see TutorialActivity
 * @see TutorialPagerAdapter
 */
public class TutorialPageFragment extends Fragment {

    /**
     * The tutorial image resource for this page.
     * <p>
     * Valid values are :
     * <ul>
     * <li>{@code R.drawable.tutorial_1}
     * <li>{@code R.drawable.tutorial_2}
     * <li>{@code R.drawable.tutorial_3}
     * <li>{@code R.drawable.tutorial_4}
     * <li>{@code R.drawable.tutorial_5}
     * </ul>
     * <p>
     * default value {@code R.drawable.tutorial_1}
     */
    public static final String PAGE_ARG = "page";

    private int _page = R.drawable.tutorial_1;

    /**
     * Factory method to create a {@link TutorialPageFragment} with the given
     * image resource.
     *
     * @param page The tutorial image resource for this page.
     *            <p>
     *            Valid values are :
     *            <ul>
     *            <li>{@code R.drawable.tutorial_1}
     *            <li>{@code R.drawable.tutorial_2}
     *            <li>{@code R.drawable.tutorial_3}
     *            <li>{@code R.drawable.tutorial_4}
     *            <li>{@code R.drawable.tutorial_5}
     *            </ul>
     * @return {@link TutorialPageFragment}
     */
    public static TutorialPageFragment create(int page) {
        Bundle args = new Bundle();
        args.putInt(PAGE_ARG, page);
        TutorialPageFragment fragment = new TutorialPageFragment();
        fragment.setArguments(args);
        return fragment;
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (getArguments().containsKey(PAGE_ARG)) {
            _page = getArguments().getInt(PAGE_ARG);
        }
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
            Bundle savedInstanceState) {
        ImageView rootView = (ImageView) inflater.inflate(
                R.layout.fragment_tutorial_page, container, false);
        rootView.setImageResource(_page);

        return rootView;
    }
}
