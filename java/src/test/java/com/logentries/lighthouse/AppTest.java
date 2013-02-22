package com.logentries.lighthouse;

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
	LighthouseClient lc = new LighthouseClient("127.0.0.1", 8001);
	/* */
	try {
		System.err.println("info>> " + lc.info());
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
        assertTrue( true );
    }
}
