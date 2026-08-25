package com.example.shop;

import java.util.ArrayList;
import java.util.List;

/**
 * A deliberately bad class: three unrelated responsibilities (pricing,
 * persistence, reporting) sharing no state between them, reaching into
 * Customer for its data, and one method that concentrates the logic.
 *
 * It exists to prove the detection strategies fire on code that genuinely has
 * the symptoms, not merely on code that is long.
 */
public class OrderManager {

    private List<String> auditLog = new ArrayList<>();
    private String connectionUrl;
    private int retryCount;
    private double taxRate;
    private String reportFormat;
    private boolean verbose;

    public double priceOrder(Customer customer, int quantity, double base,
                             double discount, boolean express, String currency) {
        double total = base * quantity;
        for (int i = 0; i < quantity; i++) {
            if (customer.getTier() > 2) {
                if (customer.getBalance() > 1000) {
                    if (express && customer.getRegion() != null) {
                        total = total - discount;
                        if (customer.getYearsActive() > 5) {
                            total = total * 0.9;
                        } else if (customer.getOrders() > 100) {
                            total = total * 0.95;
                        }
                    } else {
                        total = total + discount;
                    }
                } else if (customer.getBalance() < 0) {
                    total = total * 1.1;
                }
            }
            if (currency.equals("EUR") || currency.equals("USD")) {
                total = total * 1.02;
            }
            if (customer.getName() != null && customer.getEmail() != null) {
                total = total - 1;
            }
        }
        double tax = total * taxRate;
        while (tax > 100) {
            tax = tax / 2;
        }
        switch (quantity) {
            case 1:
                total += 5;
                break;
            case 2:
                total += 3;
                break;
            default:
                break;
        }
        return total + tax;
    }

    public void connect() {
        retryCount = 0;
    }

    public void disconnect() {
        retryCount = 0;
    }

    public String buildReport() {
        return reportFormat;
    }

    public void setReportFormat(String format) {
        this.reportFormat = format;
    }

    public void log(String message) {
        auditLog.add(message);
    }

    public List<String> getAuditLog() {
        return auditLog;
    }

    public void setVerbose(boolean verbose) {
        this.verbose = verbose;
    }

    public String getConnectionUrl() {
        return connectionUrl;
    }
}

class Customer {

    private int tier;
    private double balance;
    private String region;
    private int yearsActive;
    private int orders;
    private String name;
    private String email;

    public int getTier() {
        return tier;
    }

    public double getBalance() {
        return balance;
    }

    public String getRegion() {
        return region;
    }

    public int getYearsActive() {
        return yearsActive;
    }

    public int getOrders() {
        return orders;
    }

    public String getName() {
        return name;
    }

    public String getEmail() {
        return email;
    }
}
