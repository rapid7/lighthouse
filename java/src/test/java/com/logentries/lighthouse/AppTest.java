package com.logentries.lighthouse;

import java.util.Map;
import org.json.simple.JSONObject;

import java.util.Random;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

/**
 * Unit test for Lighthouse Client.
 */
public class AppTest {
	private class RandomObject {
		public String mPath;
		public Map<String, Object> mObj;
		public Double mValue;

		public RandomObject(final String path, final Map<String, Object> obj, final Double value) {
			mPath = path;
			mObj = obj;
			mValue = value;
		}
	}

	@SuppressWarnings("unchecked")
	private RandomObject randomObj(final Random rand) {
		Map<String, Object> first = new JSONObject();
		Map<String, Object> last = first;
		final int LEN = 20;
		String path = "";
		for (int i = 0; i < LEN; ++i) {
			final String part = "" + rand.nextInt();
			Map<String, Object> mid = new JSONObject();
			last.put(part, mid = new JSONObject());
			last = mid;
			path += part + '/';
		}
		path += "XXX";

		final Double value = rand.nextDouble();
		last.put("XXX", value);

		return new RandomObject(path, first, value);
	}

    @SuppressWarnings("unchecked")
	@Test
    public void testApp() {
		LighthouseClient lc = new LighthouseClient("127.0.0.1", 8001);
		int sequence = -1;
		int valueXXX = -1;
	
		/* */
		try {
			Map<String, Object> root = new JSONObject();
			root.put("XXX", 256);
			root.put("X", "good bye");
			root.put("abc", "Everything Works");
			Copy copy = new Copy(new Version(0, "edcba"), root);
			lc.copy(copy);
		} catch (LighthouseException e) {
			e.printStackTrace();
			fail("Cannot push initial data to the sever :-(");
		}
	
		try {
			System.err.println("info>> " + lc.state());
			sequence = lc.state().getVersion().getSequence();
		} catch (LighthouseException e) {
			fail("Cannot retrieve info about state");
		}
		assertEquals(sequence, 0);
		
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
		assertEquals(valueXXX, 256);

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
			Map<String, Object> data = new JSONObject();
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
