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

import com.amazonaws.auth.AWSCredentialsProvider;
import com.amazonaws.auth.CognitoCachingCredentialsProvider;
import com.amazonaws.regions.Regions;
import com.numenta.core.data.CoreDatabase;
import com.numenta.core.service.DataSyncService;
import com.numenta.core.service.YOMPService;
import com.numenta.core.service.NotificationService;
import com.numenta.core.utils.BackgroundThreadFactory;
import com.numenta.core.utils.Log;
import com.numenta.taurus.data.MarketCalendar;
import com.numenta.taurus.data.TaurusDataFactory;
import com.numenta.taurus.data.TaurusDatabase;
import com.numenta.taurus.service.TaurusClient;
import com.numenta.taurus.service.TaurusClientFactory;
import com.numenta.taurus.service.TaurusDataSyncService;
import com.numenta.taurus.service.TaurusNotificationService;

import android.content.Context;
import android.content.SharedPreferences;
import android.preference.PreferenceManager;

import java.net.MalformedURLException;
import java.util.Collection;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Maintain global application state.
 */
public class TaurusApplication extends com.numenta.core.app.YOMPApplication {

    private static final String TAG = TaurusApplication.class.getSimpleName();

    /** Favorite List Property */
    public static final String FAVORITE_PROPERTY = "favorite";

    /** Market Calendar Property */
    public static final String CALENDAR_PROPERTY = "calendar";

    /** Preferences file name used to save user favorites */
    private static final String FAVORITE_PREFERENCE_FILE = "favorites";

    /** Data factory used to create Taurus specific data objects */
    private TaurusDataFactory _dataFactory;

    /** Current market calendar to use. Default to US market */
    private MarketCalendar _marketCalendar = MarketCalendar.US;

    /** AWS Credential provider used to get short lived authorizations to AWS resources */
    private AWSCredentialsProvider _awsCredentialsProvider;

    @Override
    public void onCreate() {
        /*
        Initialize AWS credential provider

        Taurus uses the Amazon Cognito Identity service and AWS Security Token Service to create
        temporary, short-lived sessions used for authentication.

        The Cognito Identity Pool is passed at build time via the "COGNITO_POOL_ID" system property.

        Use "gradle -DCOGNITO_POOL_ID=us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxxx" to change the
        cognito pool id. You may also update your "gradle.properties" file with the following entry:

            systemProp.COGNITO_POOL_ID="us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxxx"

        DynamoDB Tables accessible by Taurus should be given read access to the roles associated
        with the cognito pool id.

        For more information on how to setup these roles please refer to AWS Cognito documentation.
        */
        if (BuildConfig.SERVER_URL == null && BuildConfig.COGNITO_POOL_ID != null) {
            _awsCredentialsProvider = new CognitoCachingCredentialsProvider(this,
                    BuildConfig.COGNITO_POOL_ID, Regions.US_EAST_1
            );
        }

        // Initialize Data factory
        _dataFactory = new TaurusDataFactory();

        // Initialize API Client factory
        setYOMPClientFactory(new TaurusClientFactory());

        // Initialize preferences
        PreferenceManager.setDefaultValues(this, R.xml.preferences, false);
        super.onCreate();
    }

    /**
     * Checks whether the given instance was marked as a favorite by the user
     *
     * @param instance The instance ID to check
     * @return {@code true} if it is a favorite, {@code false} otherwise
     */
    public static boolean isInstanceFavorite(String instance) {
        SharedPreferences favorites = getContext()
                .getSharedPreferences(FAVORITE_PREFERENCE_FILE, Context.MODE_PRIVATE);
        return favorites.contains(instance);
    }

    /**
     * Return a collection with all instances marked as favorite by the user
     */
    public static Collection<String> getFavoriteInstances() {
        SharedPreferences favorites = getContext()
                .getSharedPreferences(FAVORITE_PREFERENCE_FILE, Context.MODE_PRIVATE);
        return favorites.getAll().keySet();
    }

    /**
     * Add the given instance to the user's preference list.
     * This method will fire {@link #FAVORITE_PROPERTY} event.
     *
     * @param instance The instance ID to add
     */
    public static void addInstanceToFavorites(String instance) {
        SharedPreferences favorites = getContext()
                .getSharedPreferences(FAVORITE_PREFERENCE_FILE, Context.MODE_PRIVATE);
        // The long value is used to store the last time this instance fired a notification
        favorites.edit().putLong(instance, 0).apply();
        firePropertyChange(FAVORITE_PROPERTY, null, instance);
    }

    /**
     * Return the last time a notification was fired for the give instance
     *
     * @param instance The instance Id to check
     * @return The timestamp for the last time the given instance fired a notification, 0 for never
     */
    public static long getLastNotificationTime(String instance) {
        SharedPreferences favorites = getContext()
                .getSharedPreferences(FAVORITE_PREFERENCE_FILE, Context.MODE_PRIVATE);
        try {
            return favorites.getLong(instance, 0);
        } catch (ClassCastException e) {
            // Fix for legacy favorite storage where the value stored was just a boolean
            favorites.edit().putLong(instance, 0).apply();
        }
        return 0;
    }

    /**
     * Updates the last time the give instance fired a notification
     *
     * @param instance  The instance Id to update
     * @param timestamp The timestamp of the last notification
     */
    public static void setLastNotificationTime(String instance, long timestamp) {
        SharedPreferences favorites = getContext()
                .getSharedPreferences(FAVORITE_PREFERENCE_FILE, Context.MODE_PRIVATE);
        favorites.edit().putLong(instance, timestamp).apply();
    }

    /**
     * Remove the given instance from the user's favorite list
     * This method will fire {@link #FAVORITE_PROPERTY} event.
     *
     * @param instance The instance ID to remove
     */
    public static void removeInstanceFromFavorites(String instance) {
        SharedPreferences favorites = getContext()
                .getSharedPreferences(FAVORITE_PREFERENCE_FILE, Context.MODE_PRIVATE);
        favorites.edit().remove(instance).apply();
        firePropertyChange(FAVORITE_PROPERTY, instance, null);
    }

    public static TaurusApplication getInstance() {
        return (TaurusApplication) com.numenta.core.app.YOMPApplication.getInstance();
    }

    /**
     * Override this method to create <b>Taurus</b> specific database interface
     *
     * @return {@link com.numenta.taurus.data.TaurusDatabase} instance
     */
    @Override
    protected CoreDatabase createDatabase() {
        return new TaurusDatabase(getContext(), _dataFactory);
    }

    /**
     * Returns interface to taurus database
     */
    public static TaurusDatabase getDatabase() {
        return (TaurusDatabase) com.numenta.core.app.YOMPApplication.getDatabase();
    }

    /**
     * Returns factory used to create taurus data objects
     */
    public TaurusDataFactory getDataFactory() {
        TaurusApplication instance = getInstance();
        if (instance != null) {
            return instance._dataFactory;
        }
        return null;
    }

    /**
     * Factory used to create a new Data Synchronization service allowing subclasses to override
     * and
     * extend  with their own Synchronization service.
     */
    @Override
    public DataSyncService createDataSyncService(YOMPService service) {
        return new TaurusDataSyncService(service);
    }

    /**
     * Factory used to create a new notification service allowing subclasses to override and extend
     * with their own notification service.
     */
    @Override
    public NotificationService createNotificationService(YOMPService service) {
        return new TaurusNotificationService(service);
    }

    /**
     * Establish a connection to the Taurus server and returns a new instance of
     * {@link com.numenta.taurus.service.TaurusClient}
     *
     * @return {@link com.numenta.taurus.service.TaurusClient} object used to interact with the
     * server.
     */
    public static TaurusClient connectToTaurus() {
        TaurusApplication instance = getInstance();
        if (instance != null) {
            try {
                return (TaurusClient) instance.connectToServer();
            } catch (MalformedURLException e) {
                Log.e(TAG, "Failed to connect to taurus", e);
            }
        }
        return null;
    }

    /**
     * Return the current market calendar
     *
     * @see com.numenta.taurus.data.MarketCalendar
     */
    public static MarketCalendar getMarketCalendar() {
        TaurusApplication instance = getInstance();
        if (instance != null) {
            return instance._marketCalendar;
        }
        // Default to US market
        return MarketCalendar.US;
    }

    /**
     * Changes the current market calendar to use in the application.
     * <p>This method will fire {@link #CALENDAR_PROPERTY} event if the new value is different.</p>
     *
     * @param calendar The new market calendar to use.
     * @see MarketCalendar#US
     */
    public static void setMarketCalendar(MarketCalendar calendar) {
        TaurusApplication instance = getInstance();
        if (instance != null) {
            MarketCalendar old = instance._marketCalendar;
            if (old != calendar) {
                instance._marketCalendar = calendar;
                firePropertyChange(CALENDAR_PROPERTY, old, calendar);
            }
        }
    }

    /**
     * Returns the AWS Credential Provider used by Taurus to get short lived authorizations to AWS
     * resources such as DynamoDB
     */
    public static AWSCredentialsProvider getAWSCredentialProvider() {
        TaurusApplication instance = getInstance();
        if (instance != null) {
            return instance._awsCredentialsProvider;
        }
        return null;
    }
}
