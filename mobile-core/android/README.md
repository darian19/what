Mobile Core Libraries for Android
=================================
This library should be composed of all reusable **mobile core** components for the **android** platform. The components in this library should provide the basic functionality common to all Numenta android based applications.

###Usage:

 1. Create a new application project using **Android Studio** 
 1. Add these lines to your `settings.gradle` file:
    
    ```groovy
    include ':mobile-core'
	project(':mobile-core').projectDir = file('../../mobile-core/android')
    ```
 1. Add `mobile-core` as a dependency to the app's `build.gradle` file:
    
    ```groovy
    dependencies {
        compile fileTree(dir: 'libs', include: ['*.jar'])
        compile project(':mobile-core')
    }
    ```
 1. Now you can access **mobile core** classes from the `com.numenta.core` packages:
    
    ```java
    import com.numenta.core.*;
    ```