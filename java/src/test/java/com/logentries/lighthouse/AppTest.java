package com.logentries.lighthouse;

import java.util.Map;
import org.json.simple.JSONValue;
import org.json.simple.JSONObject;

import java.util.Random;

//import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestSuite;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.fail;

/**
 * Unit test for simple App.
 */
public class AppTest {
	private class RandomObject {
		public String mPath;
		public Map mObj;
		public Double mValue;

		public RandomObject(final String path, final Map obj, final Double value) {
			mPath = path;
			mObj = obj;
			mValue = value;
		}
	}

	private RandomObject randomObj(final Random rand) {
		Map first = new JSONObject();
		Map last = first;
		final int LEN = 20;
		String path = "";
		for (int i = 0; i < LEN; ++i) {
			final String part = "" + rand.nextInt();
			Map mid = new JSONObject();
			last.put(part, mid = new JSONObject());
			last = mid;
			path += part + '/';
		}
		path += "XXX";

		final Double value = rand.nextDouble();
		last.put("XXX", value);

		return new RandomObject(path, first, value);
	}

    @Test
    public void testApp()
    {
	LighthouseClient lc = new LighthouseClient("172.16.11.103", 8001);
	int sequence;
	int valueXXX;

	/* */
	try {
		System.err.println("info>> " + lc.state());
		sequence = lc.state().getVersion().getSequence();
	} catch (LighthouseException e) {
		fail("Cannot retrieve info about state");
	}
	/* */
	try {
		System.err.println("data>> " + lc.data(""));
	} catch (LighthouseException e) {
		fail("Cannot retrieve data");
	}
	/* */
	try {
		lc.data("not/found");
		fail("Retrieved non-existend location");
	} catch (LighthouseException e) {
		assertEquals("Accessing not/found", FileNotFoundLighthouseException.class, e.getClass());
	}
	/* */
	try {
		valueXXX = ((Number)lc.data("XXX")).intValue();
	} catch (LighthouseException e) {
		fail("Cannot find /XXX");
	}
	/* */
	try {
		System.err.println("data/xxx>> " + lc.data("/xxx"));
	} catch (LighthouseException e) {
		assertEquals("Accessing xxx", FileNotFoundLighthouseException.class, e.getClass());
	}
	/* */
	try {
		System.err.println("copy>> " + lc.copy());
	} catch (LighthouseException e) {
		fail("Cannot get copy");
	}
	/* */
	try {
		Random rand = new Random();
		final String lockCode = "" + rand.nextInt();
		lc.acquireLock(lockCode);
		/* */
		Map data = new JSONObject();
		data.put("Everything", "Works");
		RandomObject ro = randomObj(rand);
		data.put("XXX", ro.mObj);
		System.err.println("XXX -> " + data);
		System.err.println("path -> " + ro.mPath);
		lc.update("XXX", ro.mObj);
		lc.commit();
		final Double value = ((Number)lc.data("XXX" + '/' + ro.mPath)).doubleValue();
		assertEquals(ro.mValue, value);
	} catch (LighthouseException e) {
		fail("Cannot create complicated path: " + e);
	}
	/* */
	try {
		lc.acquireLock("x");
		lc.acquireLock("y");
		fail("We are allowed to acquire two locks at the same time");
	} catch (Exception e) {
		assertEquals("Lock x and y", LockAlreadyAcquiredLighthouseException.class, e.getClass());
	}
	/* */
	try {
		lc.rollback();
	} catch (LighthouseException e) {
		fail("Cannot release previously acquired key");
	}
	/* */
	try {
		lc.commit();
		fail("We were seccessful to commit without lock");
	} catch (Exception e) {
		assertEquals("Commiting lock no lock", LockNotAcquiredLighthouseException.class, e.getClass());
	}
	/* */
	try {
		lc.acquireLock("zzz");
	} catch (LighthouseException e) {
		fail("Cannot acquire lock `zzz'");
	}
	/* */
	try {
		lc.deleteX("12/34/56/not/found");
	} catch (Exception e) {
		assertEquals("Try to delete under zzz", FileNotFoundLighthouseException.class, e.getClass());
	}
	/* */
	try {
		lc.update("12/34/56/not/found", new Integer(123456));
	} catch (Exception e) {
		assertEquals("Try to update under zzz", FileNotFoundLighthouseException.class, e.getClass());
	}
	/* */
	try {
		lc.rollback();
	} catch (LighthouseException e) {
		fail("Cannot release lock `xxx'");
	}
    }
}
