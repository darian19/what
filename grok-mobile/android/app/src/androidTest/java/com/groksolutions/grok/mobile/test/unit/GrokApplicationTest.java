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

import com.YOMPsolutions.YOMP.mobile.YOMPApplication;
import com.YOMPsolutions.YOMP.mobile.SortOrder;
import com.YOMPsolutions.YOMP.mobile.service.YOMPClientImpl;
import com.numenta.core.utils.mock.MockYOMPClient;
import com.numenta.core.utils.mock.MockYOMPClientFactory;

import android.test.ApplicationTestCase;
import android.test.suitebuilder.annotation.SmallTest;

/**
 * TODO Document
 */
public class YOMPApplicationTest extends ApplicationTestCase<YOMPApplication> {

    public YOMPApplicationTest() {
        super(YOMPApplication.class);
    }

    @Override
    protected void setUp() throws Exception {
        super.setUp();
        createApplication();
        YOMPApplication.getInstance().setYOMPClientFactory(new MockYOMPClientFactory(new MockYOMPClient(
                YOMPClientImpl.YOMP_SERVER_LATEST)));
        YOMPApplication.stopServices();
    }

    @Override
    protected void tearDown() throws Exception {
        super.tearDown();
    }

    /**
     * Test method for {@link com.YOMPsolutions.YOMP.mobile.YOMPApplication#getSort()}.
     */
    @SmallTest
    public final void testGetSort() {
        YOMPApplication.setSort(SortOrder.Name);
        assertEquals(SortOrder.Name, YOMPApplication.getSort());
    }

    /**
     * Test method for
     * {@link com.YOMPsolutions.YOMP.mobile.YOMPApplication#getMetricUnit(String)}.
     */
    @SmallTest
    public final void testGetMetricUnit() {
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/AutoScaling/GroupTotalInstances"));
        assertEquals("Count",
                YOMPApplication.getMetricUnit("AWS/DynamoDB/ConsumedReadCapacityUnits"));
        assertEquals("Count",
                YOMPApplication.getMetricUnit("AWS/DynamoDB/ConsumedWriteCapacityUnits"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/DynamoDB/ReturnedItemCount"));
        assertEquals("Milliseconds",
                YOMPApplication.getMetricUnit("AWS/DynamoDB/SuccessfulRequestLatency"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/EBS/VolumeQueueLength"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/EBS/VolumeReadBytes"));
        assertEquals("Seconds", YOMPApplication.getMetricUnit("AWS/EBS/VolumeTotalReadTime"));
        assertEquals("Seconds", YOMPApplication.getMetricUnit("AWS/EBS/VolumeTotalWriteTime"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/EBS/VolumeWriteBytes"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/EC2/CPUUtilization"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/EC2/DiskReadBytes"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/EC2/DiskWriteBytes"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/EC2/NetworkIn"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/EC2/NetworkOut"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/ElastiCache/CPUUtilization"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/ElastiCache/NetworkBytesIn"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/ElastiCache/NetworkBytesOut"));
        assertEquals("Seconds", YOMPApplication.getMetricUnit("AWS/ELB/Latency"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/ELB/RequestCount"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/cpu/idle"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/cpu/nice"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/cpu/system"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/cpu/user"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/cpu/waitio"));
        assertEquals("None", YOMPApplication.getMetricUnit("AWS/OpsWorks/load/5"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/memory/buffers"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/memory/cached"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/memory/free"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/memory/swap"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/memory/total"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/OpsWorks/memory/used"));
        assertEquals("None", YOMPApplication.getMetricUnit("AWS/OpsWorks/procs"));
        assertEquals("Percent", YOMPApplication.getMetricUnit("AWS/RDS/CPUUtilization"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/RDS/DatabaseConnections"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/RDS/DiskQueueDepth"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/RDS/FreeableMemory"));
        assertEquals("Count/Second", YOMPApplication.getMetricUnit("AWS/RDS/ReadIOPS"));
        assertEquals("Seconds", YOMPApplication.getMetricUnit("AWS/RDS/ReadLatency"));
        assertEquals("Bytes/Second", YOMPApplication.getMetricUnit("AWS/RDS/ReadThroughput"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/RDS/SwapUsage"));
        assertEquals("Count/Second", YOMPApplication.getMetricUnit("AWS/RDS/WriteIOPS"));
        assertEquals("Seconds", YOMPApplication.getMetricUnit("AWS/RDS/WriteLatency"));
        assertEquals("Bytes/Second", YOMPApplication.getMetricUnit("AWS/RDS/WriteThroughput"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/Redshift/DatabaseConnections"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/SNS/NumberOfMessagesPublished"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/SQS/NumberOfEmptyReceives"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/SQS/NumberOfMessagesDeleted"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/SQS/NumberOfMessagesSent"));
        assertEquals("Count", YOMPApplication.getMetricUnit("AWS/SQS/NumberOfMessagesReceived"));
        assertEquals("Bytes", YOMPApplication.getMetricUnit("AWS/SQS/SentMessageSize"));
    }
}
