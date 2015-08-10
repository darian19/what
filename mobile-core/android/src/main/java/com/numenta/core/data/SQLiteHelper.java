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

package com.numenta.core.data;

import com.numenta.core.utils.DataUtils;
import com.numenta.core.utils.Log;

import android.annotation.TargetApi;
import android.content.Context;
import android.content.res.AssetManager;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.os.Build;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.util.Arrays;

/**
 * Wraps the {@link android.database.sqlite.SQLiteOpenHelper} class
 */
public class SQLiteHelper extends SQLiteOpenHelper {

    private static final String TAG = SQLiteHelper.class.getSimpleName();

    final Context _context;

    /**
     * Create a helper object to create, open, and/or manage a database.
     * This method always returns very quickly.  The database is not actually
     * created or opened until one of {@link #getWritableDatabase} or
     * {@link #getReadableDatabase} is called.
     *
     * @param context to use to open or create the database
     * @param name    of the database file, or null for an in-memory database
     * @param version number of the database (starting at 1); if the database is older,
     *                {@link #onUpgrade} will be used to upgrade the database; if the database is
     *                newer, {@link #onDowngrade} will be used to downgrade the database
     */
    public SQLiteHelper(Context context, String name, int version) {
        super(context, name, null, version);
        _context = context;
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        // Create a new database schema using the SQL script stored in "db_migrations/createdb.sql"
        AssetManager assets = _context.getAssets();
        InputStream stream = null;
        try {
            // Execute Core DB Scripts
            String scriptName = "createdb.sql";
            stream = assets.open("db_migrations/" + scriptName);
            String script = DataUtils.readTextStream(stream);
            executeSQLScript(db, script);
            Log.i(TAG, "Executed migration script : db_migrations/" + scriptName);

            // Execute App specific DB scripts if available
            try {
                stream = assets.open("app/db_migrations/" + scriptName);
                script = DataUtils.readTextStream(stream);
                executeSQLScript(db, script);
                Log.i(TAG, "Executed migration script : app.db_migrations/" + scriptName);
            } catch (FileNotFoundException e) {
                // Ignore
            }
        } catch (IOException e) {
            // Pass exception if we fail to open the create script
            throw new RuntimeException("Failed to create database", e);
        } finally {
            if (stream != null) {
                try {
                    stream.close();
                } catch (IOException e) {
                    // Ignore
                }
            }
        }
    }

    /**
     * Execute a multi-line SQL statement
     */
    void executeSQLScript(SQLiteDatabase db, String script) {
        if (script == null || script.trim().isEmpty()) {
            return; // Empty script
        }
        String[] statements = script.split(";");
        String sql;
        for (String statement : statements) {
            sql = statement.trim();
            if (!sql.isEmpty()) {
                db.execSQL(sql);
            }
        }
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        // Migration is only supported from version 22.
        // Prior to version 22 the database will be recreated and the data will be lost.
        if (oldVersion < 22) {
            onCreate(db);
            return;
        }

        // Migrate the database from the "oldVersion" to the "newVersion" by running
        // migration scripts stored in the "/assets/db_migrations" location.
        // The scripts must be named after the new version and should contain the necessary
        // SQL script used to migrate from the "oldVersion" to the next version.
        // Each SQL script will run in order updating the database to the next version.
        // For example, the file "/assets/db_migrations/23.sql" contains the SQL script required
        // to update the database from version "22" to version "23" and so on.
        InputStream stream = null;
        String script;
        String scriptName;
        AssetManager assets = _context.getAssets();
        try {
            String[] coreMigrations = assets.list("db_migrations");
            String[] appMigrations = assets.list("app/db_migrations");
            Arrays.sort(coreMigrations);
            Arrays.sort(appMigrations);
            // Run database migrations
            for (int i = oldVersion; i < newVersion; i++) {
                scriptName = (i + 1) + ".sql";
                if (Arrays.binarySearch(coreMigrations, scriptName) > 0) {
                    stream = assets.open("db_migrations/" + scriptName);
                    script = DataUtils.readTextStream(stream);
                    executeSQLScript(db, script);
                    Log.i(TAG, "Executed migration script : db_migrations/" + scriptName);
                }

                // Execute App specific DB scripts if available
                if (Arrays.binarySearch(appMigrations, scriptName) > 0) {
                    stream = assets.open("app/db_migrations/" + scriptName);
                    script = DataUtils.readTextStream(stream);
                    executeSQLScript(db, script);
                    Log.i(TAG, "Executed migration script :" + "app/db_migrations/" + scriptName);
                }
            }
        } catch (IOException e) {
            // Ignore
        } finally {
            if (stream != null) {
                try {
                    stream.close();
                } catch (IOException e) {
                    // Ignore
                }
            }
        }

    }

    @Override
    public void onOpen(SQLiteDatabase db) {
        // Enable foreign key support
        if (Build.VERSION.SDK_INT == Build.VERSION_CODES.ICE_CREAM_SANDWICH_MR1) {
            // Android 4.0.3 (API 15)
            db.execSQL("PRAGMA foreign_keys=1");
            applyOptimizationFlags(db);
        }
    }

    void applyOptimizationFlags(SQLiteDatabase db) {

        // From SQLite documentation:
        // http://www.sqlite.org/pragma.html#pragma_synchronous
        // "When synchronous is NORMAL (1), the SQLite database engine will
        // still sync at the most critical moments, but less often than in
        // FULL mode. There is a very small (though non-zero) chance that a
        // power failure at just the wrong time could corrupt the database
        // in NORMAL mode. But in practice, you are more likely to suffer a
        // catastrophic disk failure or some other unrecoverable hardware
        // fault".
        db.execSQL("PRAGMA synchronous=NORMAL");

        // From SQLite documentation:
        // http://developer.android.com/reference/android/database/sqlite/SQLiteDatabase.html#enableWriteAheadLogging()
        // "This method enables parallel execution of queries from multiple
        // threads on the same database. It does this by opening multiple
        // connections to the database and using a different database
        // connection for each query. The database journal mode is also
        // changed to enable writes to proceed concurrently with reads."
        db.enableWriteAheadLogging();
    }

    @TargetApi(Build.VERSION_CODES.JELLY_BEAN)
    @Override
    public void onConfigure(SQLiteDatabase db) {
        // Enable foreign key support
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN) {
            // Android 4.1+ (API 16+)
            db.setForeignKeyConstraintsEnabled(true);
            applyOptimizationFlags(db);
        }
    }

}
