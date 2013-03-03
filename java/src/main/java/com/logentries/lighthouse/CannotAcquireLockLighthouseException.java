package com.logentries.lighthouse;

public class CannotAcquireLockLighthouseException extends LighthouseException {
	public CannotAcquireLockLighthouseException(final String lockKey, final AccessDeniedLighthouseException caused) {
		super(String.format("Cannot acquire lock: [%s]", lockKey), caused);
	}
}
