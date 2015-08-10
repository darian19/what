# Taurus Mobile Applications #

## Android ##

### Requirements: ###

 - Android 4.1+ / API 16+ ("JellyBean" or above)
 - "Normal" screen size or higher
 - "High Density (hdpi)" or better

 See Android versions dashboard for more information:
  - http://developer.android.com/about/dashboards/index.html

The application was designed and tested on "Nexus 4".

### Development Environment ###

- Install **Java JDK** version 1.7 or higher from http://www.oracle.com/technetwork/java/javase/downloads/index.html
- Install **Android SDK** from https://developer.android.com/sdk/index.html or **homebrew** with the command:

        brew install android-sdk

- Make sure to install the latest android SDK using the following command:

        android update sdk

- The project is based on `gradle` and the new **Android Studio IDE**. It will **NOT** work with the legacy **eclipse IDE**. You can downloaded **Android Studio IDE** from https://developer.android.com/sdk/installing/studio.html

### System properties (gradle.properties) ###

- Add `gradle.properties` file to your android folder with the following values:

        # Google Analytics Tracking ID
        systemProp.GA_TRACKING_ID = "UA-XXXXXXXX-X"

        # Email address to send user feedback
        systemProp.FEEDBACK_EMAIL = "support@domain.tld"

        # AWS Cognito Identity Pool ID
        #
        # Taurus uses the Amazon Cognito Identity service and AWS Security Token Service to create
        # temporary, short-lived sessions used for authentication
        # DynamoDB Tables accessible by Taurus should be given read access to the roles associated
        # with the cognito pool id
        # For more information on how to setup these roles please refer to AWS Cognito documentation
        systemProp.COGNITO_POOL_ID = "us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxxx"
        # Keystore password
        systemProp.BUILD_PASSWORD = "CHANGEME"
        # Initial version code to use in addition to 'YOMPCommitCount'
        systemProp.INITIAL_VERSION_CODE=480


### Running Tests with Gradle ###

- Add `local.properties` file to your android folder with the following values:

        sdk.dir=/usr/local/opt/android-sdk

- This project includes the __gradle wrapper__ so there is no need to install `gradle` separately.
- To build execute ```gradlew build```
- To test, launch the  emulator first or plug your device in via USB, then execute:

        gradlew connectedCheck

- The test reports will be generated in build/outputs/reports folder:

    [android/build/taurus-mobile/outputs/reports/androidTests/connected/index.html](android/build/taurus-mobile/outputs/reports/androidTests/connected/index.html)

### Running Functional Tests with Maven ###

See [tests/behavioral/TaurusMobileApp/README.md](tests/behavioral/TaurusMobileApp/README.md)


### Running the Pipeline ###

In order to run the pipeline, you need to ensure a couple things are setup properly locally.

- Ensure the Products repo is on your `PYTHONPATH`
- Run `pip install -r pipeline/requirements.txt`
- Your **Application Signing** keystore file must be located at `/etc/numenta/products/keys/YOMP.keystore`. See [mobile-core/android/common.gradle](../mobile-core/android/common.gradle) for ways to override the default location.
- `ANDROID_HOME` environment variable should be set to the location of your Android SDK (alternatively, set this in `local.properties`)
- `BUILD_PASSWORD` environment variable must be set properly
- Run an Android device locally. You can get a list of devices using `android list avd` and launch one using `emulator -avd <avd_name>`. To create a new device use `android avd` command.
- `SAUCE_USER_NAME` environment variable must be set to Saucelabs username
- `SAUCE_KEY` environment variable must be set to Saucelabs key
- Set the `JAVA_HOME` variable in your environment to match the location of
your Java installation.


## Docker setup

### Install dependencies

- Install **VirtualBox** 4.3.10 or greater from https://www.virtualbox.org/wiki/Downloads
- Install **vagrant 1.6** or greater from http://www.vagrantup.com/downloads.html or **homebrew**:

        brew install vagrant

- Install `docker` client from http://docs.docker.com/installation or **homebrew**:

        brew install docker

### Startup

From within the `infrastructure/coreos/` directory relative to `numenta-apps` root:

        vagrant up
        source env

`vagrant up` triggers vagrant to download the CoreOS image (if necessary) and (re)launch the instance


### Build **taurus-mobile** and run tests using docker

- Copy your **Application Signing** keystore file to `.keys/YOMP.keystore` directory:

        mkdir .keys
        cp /etc/numenta/products/keys/YOMP.keystore .key/YOMP.keystore

- From `numenta-apps/taurus-mobile`:

        docker build -t taurus-mobile .

- Run default build command on docker mapping the root of `numenta-apps/` to `/opt/numenta/products`, for example:

        docker run --name taurus-mobile --rm -v `pwd`/..:/opt/numenta/products taurus-mobile

- Run custom build on docker:

        docker run --name taurus-mobile --rm -v `pwd`/..:/opt/numenta/products taurus-mobile ./gradlew clean assembleQa

