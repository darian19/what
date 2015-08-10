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

package com.YOMPsolutions.YOMP.mobile.dialog;

import android.app.AlertDialog;
import android.app.Dialog;
import android.content.DialogInterface;
import android.content.DialogInterface.OnClickListener;
import android.os.Bundle;
import android.os.Handler;
import android.support.v4.app.DialogFragment;
import android.support.v4.app.FragmentManager;

/**
 * Show a dialog for a period of time. Dismiss the dialog after the period of time has passed
 */
public class AutoDismissDialog extends DialogFragment {
    static volatile AutoDismissDialog _dialog = null;
    static final Object _lock = new Object();

    public AutoDismissDialog() {
    }

    @Override
    public Dialog onCreateDialog(Bundle savedInstanceState) {
        final Bundle args = getArguments();
        final CharSequence message = args.getCharSequence("message");
        final CharSequence title = args.getCharSequence("title");
        final long timeout = args.getLong("timeout", 0);

        final AlertDialog.Builder builder = new AlertDialog.Builder(getActivity());
        builder.setTitle(title).setMessage(message)
                .setNegativeButton(android.R.string.ok, new OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        dialog.dismiss();
                    }
                });
        final AlertDialog dialog = builder.create();
        if (timeout > 0) {
            new Handler().postDelayed(new Runnable() {
                @Override
                public void run() {
                    dialog.dismiss();
                }
            }, timeout);
        }
        return dialog;
    }

    /**
     * Create a new {@link Dialog} that will be dismissed after a period of time
     *
     * @param title The dialog title
     * @param message The dialog message to display
     * @param timeout Time in milliseconds to dismiss the dialog
     * @param manager The FragmentManager this fragment will be added to
     */
    public static void show(CharSequence title, CharSequence message, long timeout,
            FragmentManager manager) {
        synchronized (_lock) {
            if (_dialog == null) {
                _dialog = new AutoDismissDialog();
            } else {
                return;
            }
        }
        final Bundle args = new Bundle();
        args.putCharSequence("title", title);
        args.putCharSequence("message", message);
        args.putLong("timeout", timeout);
        _dialog.setArguments(args);

        _dialog.show(manager, "AutoDismissDialog");
        _dialog = null;
    }
}
