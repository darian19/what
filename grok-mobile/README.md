# YOMP Mobile Applications #

## Android ##

### Requirements: ###

 - YOMP Server 1.6.1 or above
 - Android 4.1+ / API 16+ ("JellyBean" or above)
 - "Normal" screen size or higher
 - "High Density (hdpi)" or better

 See Android versions dashboard for more information:

  - http://developer.android.com/about/dashboards/index.html

The application was designed and tested on "Nexus 4".

### Development Environment ###

- Install **Java JDK** version 1.7 or higher from http://www.oracle.com/technetwork/java/javase/downloads/index.html
- Install **Android SDK** from https://developer.android.com/sdk/index.html
- Make sure to install the latest android SDK using the following command:

        android update sdk

- The project is based on `gradle` and the new **Android Studio IDE**. It will NOT work with the legacy `eclipse` IDE. You can downloaded **Android Studio IDE** from https://developer.android.com/sdk/installing/studio.html

### System properties (gradle.properties) ###

- Add `gradle.properties` file to your android folder with the following values:

        # Google Analytics Tracking ID
        systemProp.GA_TRACKING_ID = "UA-XXXXXXXX-X"

        # Email address to send user feedback
        systemProp.FEEDBACK_EMAIL = "support@domain.tld"

        # Initial version code to use in addition to 'YOMPCommitCount'
        systemProp.INITIAL_VERSION_CODE=1314

### Running Tests with Gradle ###

- Add ```local.properties``` file to your android folder with the following values:

        sdk.dir=/your_path_to/adt-bundle-mac-x86_64-XXXXXXX/sdk

- This project includes the __gradle wrapper__ so there is no need to install `gradle` separately.
- To build execute ```gradlew build```
- To test, launch the  emulator first or plug your device in via USB, then execute:

        gradlew -DSERVER_URL=??? -DSERVER_PASS=??? connectedCheck

- The test reports will be generated in build/outputs/reports folder:

        android/build/YOMP-mobile/outputs/reports/androidTests/connected/index.html

Example Test Execution from Gradle:

    gradlew -DSERVER_URL=https://YOMP.domain.tld -DSERVER_PASS=XXXXX connectedCheck

**NOTE** replace `YOMP.domain.tld` with the server IP or DNS entry of your YOMP instance and replace `XXXXX` with the API Key for that instance

### Running Functional Tests with Maven ###

- You will have to install Maven from https://maven.apache.org/
- You will have to set few environment variables:

        # M2_HOME={path-to-apache-maven}/apache-maven-x.x.x
        # PATH=${PATH}:$M2_HOME/bin
        # M2=$M2_HOME/bin

- As functional tests run on saucelabs you will need username and key of saucelabs.
    Following environment variables should be set:

        # SAUCE_USER_NAME=sauce-username
        # SAUCE_KEY=sauce-key

- The test reports will be generated in  tests/behavioral/YOMPMobileApp/target/surefire-reports folder:
        YOMP-mobile/tests/behavioral/YOMPMobileApp/target/surefire-reports/testng-results.xml

Example Test Execution from Maven:

    mvn install -D url="https://YOMP.domain.tld" -D pwd="XXXXX" -D deviceName="Android  Emulator" -D version="4.4" -D sauceUserName=$SAUCE_USER_NAME -D sauceAccessKey=$SAUCE_KEY

 **NOTE**  replace `YOMP.domain.tld` with the server IP or DNS entry of your YOMP instance and replace `XXXXX` with the API Key for that instance.
`deviceName` you can select platform from here https://saucelabs.com/platforms/, this code is YOMP APK is tested on "Android Emulator" and "Google Nexus 7C Emulator".
`version` this is android version for the respective emulator
`sauceUserName` and `sauceUserName` as mentioned above.


### Running the Pipeline ###

In order to run the pipeline, ensure that following things are properly setup locally.

- You will require a running instance of YOMP for testing the mobile app.
- Below are three ways to achieve:
    - Pass the region and 1.6.1 AMI-ID from the marketplace release to `run_pipeline` script. Script will take care of launching a YOMP instance.
    - Set up a bucket on S3. Create `stable_ami/ami.txt` file in the created bucket. URL will be `https://s3.amazonaws.com/<your-bucket-name>/stable_ami/ami.txt`. Contents of ami.txt should be `AMI_ID: ami-xxxxxxxx`, where `ami-xxxxxxxx` should be the
      AMI-ID. In this case you just need to pass region to `run_pipeline` and AMI-ID will be fetched by `https://s3.amazonaws.com/<your-bucket-name>/stable_ami/ami.txt`. Script will take care of launching a YOMP instance.
      **NOTE:** The code will read `<your-bucket-name>` from the `S3_MAPPING_BUCKET` environment variable
    - Pass --server-url https://YOMP.domain.tld --apikey <API> to a valid, running instance of YOMP.
- Ensure the Products repo is on your `PYTHONPATH`
- Run `pip install -r pipeline/requirements.txt`
- Your "Application Signing" keystore file must be located at `/etc/numenta/products/keys/YOMP.keystore`.
  See [mobile-core/android/common.gradle](../mobile-core/android/common.gradle) for ways to override the default location.
- `ANDROID_HOME` environment variable should be set to the location of your Android SDK (alternatively, set this in `local.properties`)
- `YOMP_MOBILE_HOME` environment variable should be set to the location of `YOMP-mobile` sources. E.g.: `~/YOMPhub/numenta/products/YOMP-mobile`
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables must be set
- `BUILD_PASSWORD` environment variable must be set properly.
- Run an Android device locally. You can get a list of devices using `android list avd` and launch one using `emulator -avd <avd_name>`