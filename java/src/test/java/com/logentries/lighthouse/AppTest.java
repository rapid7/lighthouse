package com.logentries.lighthouse;

import java.util.Map;
import org.json.simple.JSONValue;
import org.json.simple.JSONObject;

import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestSuite;

/**
 * Unit test for simple App.
 */
public class AppTest 
    extends TestCase
{
    /**
     * Create the test case
     *
     * @param testName name of the test case
     */
    public AppTest( String testName )
    {
        super( testName );
    }

    /**
     * @return the suite of tests being tested
     */
    public static Test suite()
    {
        return new TestSuite( AppTest.class );
    }

    /**
     * Rigourous Test :-)
     */
    public void testApp()
    {
	int version = 123;
        int valueXXX = 0;

	LighthouseClient lc = new LighthouseClient("127.0.0.1", 8001);
	/* */
	try {
		System.err.println("info>> " + lc.info());
		version = lc.info().getVersion();
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		System.err.println("data>> " + lc.data("/"));
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		valueXXX = ((Number)lc.data("/XXX")).intValue();
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		System.err.println("data/xxx>> " + lc.data("/xxx"));
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		System.err.println("pull>> " + lc.pull());
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		Map data = new JSONObject();
		data.put("Everything", "Works");
		data.put("XXX", new Integer(1256));
		Map data2 = new JSONObject();
		data2.put("12", new Integer(12));
		data2.put("3.14", new Float(3.14));
		data.put("x", data2);
		lc.push(new Pull(new Info(version + 1, "ADFCDADF"), data));
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		lc.acquireLock("x");
		lc.acquireLock("y");
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		lc.update("XXX", new Integer(valueXXX + 106512));
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		lc.commit();
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		lc.acquireLock("zzz");
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		lc.deleteX("12/34/56/not/found");
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		lc.update("12/34/56/not/found", new Integer(123456));
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
	/* */
	try {
		lc.rollback();
	} catch (LighthouseException e) {
		e.printStackTrace();
	}
        assertTrue( true );
    }
}
