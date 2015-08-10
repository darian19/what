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

import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.YOMPsolutions.YOMP.mobile.service.MetricDataParser;
import com.numenta.core.app.YOMPApplication;
import com.numenta.core.data.CoreDataFactory;
import com.numenta.core.data.MetricData;
import com.numenta.core.service.YOMPException;
import com.numenta.core.utils.YOMPAndroidTestCase;

import org.msgpack.MessagePack;
import org.msgpack.unpacker.Unpacker;

import android.test.suitebuilder.annotation.SmallTest;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;

public class MetricDataParserTests extends YOMPAndroidTestCase {


    @Override
    protected void setUp() throws Exception {
        super.setUp();
    }

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();
    }

    @SmallTest
    public void testParseMetricData_1_3() {
        Unpacker unpacker = null;
        try {
            CoreDataFactory factory = YOMPApplication.getDatabase()
                    .getDataFactory();
            MetricData EXPECTED = factory.createMetricData("3654d3972c1742a0bef5e0022f210544",
                    1404837900000l, 91.308f, 0.274253f, 4296);

            InputStream in = getTestData(YOMPClientImpl.YOMP_SERVER_1_3, "model_data.msgpack");
            MessagePack msgpack = new MessagePack();
            unpacker = msgpack.createUnpacker(new BufferedInputStream(in));
            MetricDataParser parser = new MetricDataParser(unpacker);
            List<MetricData> data = parser.parse();
            assertEquals(4296, data.size());
            MetricData value = data.get(0);
            assertEquals(EXPECTED.getMetricId(), value.getMetricId());
            assertEquals(EXPECTED.getAnomalyScore(), value.getAnomalyScore());
            assertEquals(EXPECTED.getMetricValue(), value.getMetricValue());
            assertEquals(EXPECTED.getRowid(), value.getRowid());
            assertEquals(EXPECTED.getTimestamp(), value.getTimestamp());
        } catch (IOException | YOMPException e) {
            fail(e.getMessage());
        } finally {
            try {
                if (unpacker != null) {
                    unpacker.close();
                }
            } catch (IOException e) {
                // Ignore
            }
        }
    }
}
