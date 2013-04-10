package com.logentries.lighthouse;

public class CannotAcquireLockLighthouseException extends LighthouseException {
	private static final long serialVersionUID = 5537331332631244701L;

	public CannotAcquireLockLighthouseException(final String lockKey, final AccessDeniedLighthouseException caused) {
		super(String.format("Cannot acquire lock: [%s]", lockKey), caused);
	}
}
