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

package com.numenta.taurus;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.MediaStore;

import java.io.File;
import java.io.FileNotFoundException;

public class ScreenShotProvider extends ContentProvider {

    private static final String _mimeType = "image/jpeg";
    private static final String[] _mimeTypes = { _mimeType };

    @Override
    public int delete(Uri arg0, String arg1, String[] arg2) {
        // ignore
        return 0;
    }

    // Set the mime/type of the file
    @Override
    public String getType(Uri arg0) {
        return _mimeType;
    }

    @Override
    public String[] getStreamTypes(Uri uri, String mimeTypeFilter) {
       return _mimeTypes;
    }

    @Override
    public Uri insert(Uri arg0, ContentValues arg1) {
        // ignore
        return null;
    }

    @Override
    public boolean onCreate() {
        // nothing to do here
        return true;
    }

    // We have to return a cursor so that android can handle appropriately; this
    // ensure that
    // a cursor is provided that will appropriately handle the image.
    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs,
            String sortOrder) {
        if (projection == null) {
            projection = new String[] {
                    MediaStore.MediaColumns.DISPLAY_NAME,
                    MediaStore.MediaColumns.SIZE,
                    MediaStore.MediaColumns._ID,
                    MediaStore.MediaColumns.MIME_TYPE
            };
        }

        final long time = System.currentTimeMillis();
        MatrixCursor result = new MatrixCursor(projection);
        final File tempFile = generatePictureFile(uri);

        Object[] row = new Object[projection.length];
        for (int i = 0; i < projection.length; i++) {

           if (projection[i].compareToIgnoreCase(MediaStore.MediaColumns.DISPLAY_NAME) == 0) {
              row[i] = uri.getLastPathSegment();
           } else if (projection[i].compareToIgnoreCase(MediaStore.MediaColumns.SIZE) == 0) {
              row[i] = tempFile.length();
           } else if (projection[i].compareToIgnoreCase(MediaStore.MediaColumns.DATA) == 0) {
              row[i] = tempFile;
           } else if (projection[i].compareToIgnoreCase(MediaStore.MediaColumns.MIME_TYPE)==0) {
              row[i] = _mimeType;
           } else if (projection[i].compareToIgnoreCase(MediaStore.MediaColumns.DATE_ADDED)==0 ||
                   projection[i].compareToIgnoreCase(MediaStore.MediaColumns.DATE_MODIFIED)==0 ||
                   projection[i].compareToIgnoreCase("datetaken")==0) {
               row[i] = time;
           } else if (projection[i].compareToIgnoreCase(MediaStore.MediaColumns._ID)==0) {
               row[i] = 0;
           } else if (projection[i].compareToIgnoreCase("orientation")==0) {
               row[i] = "vertical";
           }
        }

        result.addRow(row);
        return result;
    }

    @Override
    public int update(Uri arg0, ContentValues arg1, String arg2, String[] arg3) {
        // ignore
        return 0;
    }

    private File generatePictureFile(Uri uri) {
        return new File(getContext().getCacheDir(), uri.getPath());
    }

    // Provide access to the private file as read only
    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!mode.equals("r")) {
            throw new SecurityException("Only read access is allowed");
        }

        return ParcelFileDescriptor.open(generatePictureFile(uri), ParcelFileDescriptor.MODE_READ_ONLY);

    }

}
