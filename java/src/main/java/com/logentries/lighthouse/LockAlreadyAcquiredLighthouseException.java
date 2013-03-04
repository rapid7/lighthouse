package com.logentries.lighthouse;

public class LockAlreadyAcquiredLighthouseException extends LighthouseException {
	public LockAlreadyAcquiredLighthouseException() {
		super("Lock Already Acquired");
	}
}
