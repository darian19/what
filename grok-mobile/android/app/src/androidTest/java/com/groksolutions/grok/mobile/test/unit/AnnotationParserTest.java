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

package com.YOMPsolutions.YOMP.mobile.test.unit;

import com.YOMPsolutions.YOMP.mobile.service.AnnotationParser;
import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.Annotation;
import com.numenta.core.data.CoreDataFactory;
import com.numenta.core.utils.YOMPAndroidTestCase;

import android.util.JsonReader;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;
import java.util.List;


public class AnnotationParserTest extends YOMPAndroidTestCase {


    public void testParse() throws Exception {
        JsonReader reader = null;
        try {

            CoreDataFactory factory = YOMPApplication.getDatabase()
                    .getDataFactory();
            Annotation expected = factory.createAnnotation("f90057f34e53425194f90794e289fee4",
                    1406274900000l, 1406581436000l, "demo.device", "Demo User",
                    "us-west-2/AWS/ELB/YOMP-docs-elb", "My Demo Message", null);

            // Sample annotation file with 3 annotations
            InputStream in = getTestData(YOMPClientImpl.YOMP_SERVER_1_6, "annotation.json");
            reader = new JsonReader(new InputStreamReader(in, "UTF-8"));
            AnnotationParser parser = new AnnotationParser(reader);
            List<Annotation> annotations = parser.parse();
            assertEquals(3, annotations.size());

            Annotation actual = annotations.get(0);
            assertEquals(expected.getId(), actual.getId());
            assertEquals(expected.getTimestamp(), actual.getTimestamp());
            assertEquals(expected.getCreated(), actual.getCreated());
            assertEquals(expected.getDevice(), actual.getDevice());
            assertEquals(expected.getUser(), actual.getUser());
            assertEquals(expected.getInstanceId(), actual.getInstanceId());
            assertEquals(expected.getMessage(), actual.getMessage());
            assertEquals(expected.getData(), actual.getData());

        } catch (FileNotFoundException | UnsupportedEncodingException e) {
            fail(e.getMessage());
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    // Ignore
                }
            }
        }

    }
}
