# Database Setup using pgAdmin

This guide provides detailed, step-by-step instructions for setting up the required PostgreSQL database and user role using the pgAdmin graphical interface. After completing these steps, you can continue from **Step 2.4** in the main `README.md` file.

---

### **Step 1: Open pgAdmin and Connect to a Server**

1.  **Launch pgAdmin:** Open the pgAdmin 4 application. You may be prompted for a master password if you set one up during installation; this password is for securing pgAdmin itself, not for your database.

2.  **Register a New Server (if not already done):**
    If you don't see your local database server listed under "Servers" in the left-hand browser panel, you'll need to connect to it.
    *   On the main dashboard, click on **"Add New Server"**.
    *   Alternatively, in the browser tree, right-click on **Servers** -> **Create** -> **Server...**.

3.  **Configure the New Server Connection:**
    A dialog box will appear.
    *   **In the `General` tab:**
        *   Give your server a descriptive name, for example, `Local PostgreSQL`. This is just a label for pgAdmin.
    *   **In the `Connection` tab:**
        *   **Host name/address:** Enter `localhost`.
        *   **Port:** Keep the default, `5432`.
        *   **Maintenance database:** Keep the default, `postgres`.
        *   **Username:** Enter `postgres` (this is the default superuser created during installation).
        *   **Password:** Enter the password for the `postgres` user. You would have set this password when you installed PostgreSQL.
    *   Click **Save**. You should now see your `Local PostgreSQL` server in the browser tree. If you see a red 'X' on the icon, there might be an issue with the connection details or the database server might not be running.

---

### **Step 2: Create the Application User (Login Role)**

Now, we'll create a dedicated user (`skin`) for our application.

1.  **Navigate to Login/Group Roles:**
    *   In the browser tree, expand your server (`Local PostgreSQL`).
    *   Right-click on **Login/Group Roles** and select **Create** > **Login/Group Role...**.

2.  **Define the User's Properties:**
    *   **General Tab:** In the **Name** field, type `skin`.
    *   **Definition Tab:** In the **Password** field, type `skin`. You will need to type it again to confirm.
    *   **Privileges Tab:** Make sure the **Can login?** switch is set to `Yes`.
    *   Click **Save**.

---

### **Step 3: Create the Application Database**

Finally, let's create the `skincare` database and assign the `skin` user as its owner.

1.  **Navigate to Databases:**
    *   In the browser tree, right-click on **Databases** and select **Create** > **Database...**.

2.  **Define the Database Properties:**
    *   **General Tab:** In the **Database** field, type `skincare`.
    *   **Owner:** Select the `skin` role from the dropdown list.
    *   Click **Save**.

---

### **Next Steps**

You have now successfully created the required user (`skin`) and database (`skincare`) using pgAdmin.

Please return to the `README.md` file and proceed with **Step 2.4 Run Database Migrations**. 