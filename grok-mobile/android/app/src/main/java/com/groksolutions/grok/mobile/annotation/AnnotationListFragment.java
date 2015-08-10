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

package com.YOMPsolutions.YOMP.mobile.annotation;

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.R;
import com.numenta.core.data.Annotation;
import com.numenta.core.utils.Pair;

import android.graphics.Typeface;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.ListFragment;
import android.text.Layout;
import android.text.SpannableStringBuilder;
import android.text.style.AlignmentSpan;
import android.text.style.RelativeSizeSpan;
import android.text.style.StyleSpan;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.TextView;

import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;


/**
 * A fragment representing a list of Annotations.
 */
public class AnnotationListFragment extends ListFragment {
    private ArrayAdapter<CharSequence> _adapter;
    private List<Pair<Annotation, Boolean>> _annotations;
    private final DateFormat _dateTimeFormat = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT);
    private final DateFormat _dateFormat = DateFormat.getDateInstance(DateFormat.SHORT);
    private final DateFormat _timeFormat = DateFormat.getTimeInstance(DateFormat.SHORT);

    /**
     * Mandatory empty constructor for the fragment manager to instantiate the
     * fragment (e.g. upon screen orientation changes).
     */
    public AnnotationListFragment() {
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        _adapter = new ArrayAdapter<CharSequence>(getActivity(), R.layout.annotation_item, R.id.txt_annotation_message) {
            @Override
            public View getView(int position, View convertView, ViewGroup parent) {

                View view = super.getView(position, convertView, parent);
                if (_annotations != null && !_annotations.isEmpty()) {
                    Pair<Annotation, Boolean> pair = _annotations.get(position);
                    Annotation annotation = pair.first;
                    Boolean showDate = pair.second;
                    if (annotation != null) {
                        // Update Annotation footer
                        TextView footerTxt = (TextView) view.findViewById(R.id.txt_annotation_footer);
                        footerTxt.setText(formatAnnotationFooter(annotation, showDate));

                        // Show or Hide "delete" button if the annotation was created using the
                        // current device. The user can only delete annotations he creates
                        View deleteBtn = view.findViewById(R.id.btn_annotation_delete);
                        if (YOMPApplication.getDeviceId().equals(annotation.getDevice())) {
                            deleteBtn.setVisibility(View.VISIBLE);
                        } else {
                            deleteBtn.setVisibility(View.GONE);
                        }

                        View listItemFrame = view.findViewById(R.id.layout_list_item);
                        TextView dateTxt = (TextView) view.findViewById(R.id.txt_annotation_date);
                        View addBtn = view.findViewById(R.id.btn_annotation_add);

                        // Only show the "+" button on the last annotation for the specific time.
                        if (_annotations.size() == 1) {
                            // If we only have one annotation then show "+" button
                            addBtn.setVisibility(View.VISIBLE);
                        } else if (position < _annotations.size()-1) {
                            Annotation next = _annotations.get(position + 1).first;
                            if (next.getTimestamp() != annotation.getTimestamp()) {
                                // Last annotation for time. Show "add" button
                                addBtn.setVisibility(View.VISIBLE);
                            } else {
                                // Only show "add" button for the last annotation at specific time
                                addBtn.setVisibility(View.GONE);
                            }
                        } else {
                            // Last annotation. Show "add" button
                            addBtn.setVisibility(View.VISIBLE);
                        }

                        // Only show the annotation date before the first annotation for the specific time.
                        if (_annotations.size() == 1) {
                            // If we only have one annotation then show annotation date
                            dateTxt.setText(_dateTimeFormat.format(new Date(annotation.getTimestamp())));
                            dateTxt.setVisibility(View.VISIBLE);
                            listItemFrame.setBackgroundResource(R.drawable.annotation_background_first_item);
                        } else if (position == 0) {
                            // First annotation in List. Show annotation date
                            dateTxt.setText(_dateTimeFormat.format(new Date(annotation.getTimestamp())));
                            dateTxt.setVisibility(View.VISIBLE);
                            listItemFrame.setBackgroundResource(R.drawable.annotation_background_first_item);
                        } else {
                            Annotation prev = _annotations.get(position - 1).first;
                            if (prev.getTimestamp() != annotation.getTimestamp()) {
                                dateTxt.setText(_dateTimeFormat.format(new Date(annotation.getTimestamp())));
                                dateTxt.setVisibility(View.VISIBLE);
                                listItemFrame.setBackgroundResource(R.drawable.annotation_background_first_item);
                            } else {
                                dateTxt.setVisibility(View.GONE);
                                listItemFrame.setBackgroundResource(R.drawable.annotation_background);
                            }
                        }
                    }
                }
                return view;
            }
        };
        setListAdapter(_adapter);
    }

    /**
     * Get Annotation from the given list position
     *
     * @param position zero based list position
     *
     * @return The annotation or {@code null}
     */
    public Annotation getAnnotation(int position) {
        if (position >= 0 && position < _annotations.size()) {
            return _annotations.get(position).first;
        }
        return null;
    }

    /**
     * Get Annotation by ID
     *
     * @param id Annotation ID
     *
     * @return The annotation or {@code null}
     */
    public Annotation getAnnotationById(String id) {
        if (_annotations != null && !_annotations.isEmpty()) {
            for (Pair<Annotation, Boolean> ann : _annotations) {
                if (ann.first.getId().equals(id)) {
                    return ann.first;
                }
            }
        }
        return null;
    }


    /**
     * Format annotation message footer for list item display
     *
     * @param annotation
     * @param showDate
     * @return
     */
    SpannableStringBuilder formatAnnotationFooter(Annotation annotation, boolean showDate) {
        int pos, rightPos;

        Date created = new Date(annotation.getCreated());
        // Format text
        SpannableStringBuilder text = new SpannableStringBuilder();

        // <div align="right">
        rightPos = pos = text.length();

        //<small>6/30/14 3:25 PM - </small>

        // Show date if different annotation or if created date changed
        if (showDate) {
            text.append(_dateFormat.format(created)).append(" ");
        }
        text.append(_timeFormat.format(created)).append(" - ");
        text.setSpan(new RelativeSizeSpan(0.5f), pos, text.length(), 0);

        // User
        pos = text.length();
        text.append(annotation.getUser());
        text.setSpan(new RelativeSizeSpan(1.0f), pos, text.length(), 0);

        // </div align="right">
        text.setSpan(new AlignmentSpan.Standard(Layout.Alignment.ALIGN_OPPOSITE), rightPos, text.length(), 0);

        // Attach hidden annotation ID to the text.
        // This ID is used by the actions attached to the list
        text.setSpan(new android.text.Annotation("id", annotation.getId()), 0, text.length(), 0);

        return text;
    }

    /**
     * Format annotation message body for list item display
     *
     * @param annotation The annotation to format
     *
     * @return The formatted annotation text suitable for use with {@link android.widget.TextView}
     */
    SpannableStringBuilder formatAnnotationBody(Annotation annotation) {
        int pos;

        // Format text
        SpannableStringBuilder text = new SpannableStringBuilder();

        // <br/> My Message
        pos = text.length();
        text.append(annotation.getMessage());
        text.setSpan(new RelativeSizeSpan(1.0f), pos, text.length(), 0);
        text.setSpan(new StyleSpan(Typeface.NORMAL), pos, text.length(), 0);

        // Attach hidden annotation ID to the text.
        // This ID is used by the actions attached to the list
        text.setSpan(new android.text.Annotation("id", annotation.getId()), 0, text.length(), 0);

        return text;
    }

    /**
     * Update list with all annotations for the given server for the given range
     *
     * @param server Filter annotations by server
     * @param from   return records from this date
     * @param to     return records up to this date
     */
    public void updateList(final String server, final Date from, final Date to) {
        new AsyncTask<Void, Void, List<Annotation>>() {
            @Override
            protected void onPostExecute(final List<Annotation> result) {
                _adapter.clear();
                _annotations = new ArrayList<Pair<Annotation, Boolean>>();
                boolean showDate;

                Calendar annotationTimestamp = Calendar.getInstance();
                Calendar created = Calendar.getInstance();
                Calendar previousCreated = Calendar.getInstance();
                Calendar previousAnnotation = Calendar.getInstance();
                previousCreated.setTimeInMillis(0);
                previousAnnotation.setTimeInMillis(0);

                for (Annotation annotation : result) {
                    annotationTimestamp.setTimeInMillis(annotation.getTimestamp());
                    created.setTimeInMillis(annotation.getCreated());
                    if (previousAnnotation.getTimeInMillis() == 0) {
                        // Initialize previous values
                        previousAnnotation.setTimeInMillis(annotationTimestamp.getTimeInMillis());
                        previousCreated.setTimeInMillis(created.getTimeInMillis());
                    }
                    // Show date only if the "created" day is different from the previous day
                    if (annotationTimestamp.compareTo(previousAnnotation) != 0) {
                        // Do not show date for first annotation
                        showDate = false;
                        // Reset first date to be the annotation timestamp
                        previousCreated.setTimeInMillis(annotationTimestamp.getTimeInMillis());
                    } else if (previousCreated.get(Calendar.YEAR) != created.get(Calendar.YEAR)) {
                        showDate = true;
                    } else if (previousCreated.get(Calendar.MONTH) != created.get(Calendar.MONTH)) {
                        showDate = true;
                    } else if (previousCreated.get(Calendar.DAY_OF_MONTH) != created.get(Calendar.DAY_OF_MONTH)) {
                        showDate = true;
                    } else {
                        // The date is the same, only show time
                        showDate = false;
                    }
                    // Add formatted annotation to list
                    _annotations.add(new Pair<Annotation, Boolean>(annotation, showDate));
                    _adapter.add(formatAnnotationBody(annotation));

                    previousCreated.setTimeInMillis(created.getTimeInMillis());
                    previousAnnotation.setTimeInMillis(annotationTimestamp.getTimeInMillis());
                }
            }

            @Override
            protected List<Annotation> doInBackground(Void... params) {
                return YOMPApplication.getDatabase().getAnnotations(server, from, to);
            }
        }.execute();
    }
}
