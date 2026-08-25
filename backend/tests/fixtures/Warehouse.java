package com.example.shop;

import java.util.ArrayList;
import java.util.List;

/**
 * Fixture exercising the metric suite. The three classes below are deliberately
 * different in shape: a cohesive one, a data holder, and one that is envious of
 * the data holder.
 */
public class Warehouse {

    private final List<Item> stock = new ArrayList<>();
    private String location;

    public Warehouse(String location) {
        this.location = location;
    }

    public void add(Item item) {
        stock.add(item);
    }

    public int size() {
        return stock.size();
    }

    public String getLocation() {
        return location;
    }

    public void setLocation(String location) {
        this.location = location;
    }
}

class Item {

    public String name;
    public double price;
    public int quantity;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public double getPrice() {
        return price;
    }

    public void setPrice(double price) {
        this.price = price;
    }

    public int getQuantity() {
        return quantity;
    }

    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }
}

class InvoicePrinter {

    private String header;

    /**
     * Reads almost everything from Item and almost nothing from itself:
     * the textbook shape of Feature Envy.
     */
    public String describe(Item item) {
        double net = item.getPrice() * item.getQuantity();
        if (net > 100 && item.getName() != null) {
            return item.getName() + " costs " + net;
        }
        return item.name + "/" + item.price + "/" + item.quantity;
    }

    public String getHeader() {
        return header;
    }
}
